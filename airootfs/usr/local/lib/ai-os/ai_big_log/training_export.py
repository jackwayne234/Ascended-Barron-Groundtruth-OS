from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .logger import DEFAULT_LOG_PATH, DEFAULT_STATE_PATH, load_state, save_state
from .training_qa import SENSITIVE_PATTERNS, analyze_log

MODEL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True)
class PreparedTrainingExport:
    model_id: str
    jsonl_text: str
    summary: dict[str, Any]
    qa_report: dict[str, Any]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def validate_model_id(model_id: str) -> str:
    cleaned = (model_id or "").strip()
    if not MODEL_ID_RE.match(cleaned):
        raise ValueError("Model ID must use a basic Hugging Face owner/model-name shape, for example meta-llama/Llama-3.1-8B-Instruct.")
    return cleaned


def sanitize_model_id_for_filename(model_id: str) -> str:
    cleaned = validate_model_id(model_id)
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", cleaned)
    safe = re.sub(r"-+", "-", safe).strip("-._")
    return safe or "model"


def suggested_export_filename(model_id: str, timestamp: str | None = None) -> str:
    return f"training-data-{sanitize_model_id_for_filename(model_id)}-{timestamp or utc_stamp()}.jsonl"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception as exc:
                raise ValueError(f"Log must be valid JSONL before export; line {line_no} failed: {exc}") from exc
            if isinstance(obj, dict):
                records.append(obj)
    return records


def _message_text(record: dict[str, Any]) -> str:
    value = record.get("content")
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return json.dumps(value, ensure_ascii=False, sort_keys=True).strip()


def _conversation_examples(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    sessions: dict[str, list[dict[str, Any]]] = {}
    found = 0
    skipped_tool_or_meta = 0
    skipped_empty = 0
    for record in records:
        if record.get("record_type") != "ai_message":
            continue
        found += 1
        role = str(record.get("role") or "").strip()
        if role not in {"user", "assistant"}:
            skipped_tool_or_meta += 1
            continue
        content = _message_text(record)
        if not content:
            skipped_empty += 1
            continue
        session_id = str(record.get("session_id") or "unknown-session")
        sessions.setdefault(session_id, []).append(record | {"_export_content": content})

    examples: list[dict[str, Any]] = []
    skipped_unpaired = 0
    for session_records in sessions.values():
        session_records.sort(key=lambda r: (float(r.get("timestamp") or 0), int(r.get("message_id") or 0)))
        messages: list[dict[str, str]] = []
        saw_user = False
        saw_assistant = False
        for record in session_records:
            role = str(record.get("role"))
            if role == "user":
                saw_user = True
            elif role == "assistant":
                saw_assistant = True
            messages.append({"role": role, "content": str(record["_export_content"])})
        if saw_user and saw_assistant and len(messages) >= 2:
            examples.append({"messages": messages})
        else:
            skipped_unpaired += len(messages)

    skipped_total = skipped_tool_or_meta + skipped_empty + skipped_unpaired
    return examples, {
        "records_found": found,
        "records_prepared": len(examples),
        "records_skipped": skipped_total,
        "skipped_tool_or_meta": skipped_tool_or_meta,
        "skipped_empty": skipped_empty,
        "skipped_unpaired": skipped_unpaired,
    }


def _sensitive_finding_count(qa_report: dict[str, Any]) -> int:
    return int(qa_report.get("sensitive_findings", {}).get("count", 0) or 0)


def _warning_summary(qa_report: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if qa_report.get("overall_status") == "warn":
        warnings.append("Training QA report status is WARN; export is allowed because valid conversations were prepared.")
    findings = {
        "duplicate record IDs": qa_report.get("duplicate_record_ids", {}).get("count", 0),
        "logger errors": qa_report.get("logger_errors", {}).get("count", 0),
        "sensitive findings": qa_report.get("sensitive_findings", {}).get("count", 0),
        "timestamp backsteps": len(qa_report.get("timestamp_backsteps", [])),
        "message ID gaps": len(qa_report.get("message_id_gaps", [])),
    }
    for label, count in findings.items():
        if count:
            warnings.append(f"QA found {count} {label}.")
    return warnings


def prepare_training_export(log_path: Path | str = DEFAULT_LOG_PATH, model_id: str = "") -> PreparedTrainingExport:
    model = validate_model_id(model_id)
    path = Path(log_path).expanduser().resolve()
    qa_report = analyze_log(path)
    if not qa_report.get("readable") or not qa_report.get("valid_jsonl"):
        raise ValueError("Log must be readable and valid JSONL before export.")
    sensitive_count = _sensitive_finding_count(qa_report)
    if sensitive_count:
        raise ValueError(
            f"Sensitive data was caught by Training QA ({sensitive_count} finding(s)). "
            "Fix/redact the flagged data, rerun Prepare Training Data, then export. "
            "Open Review Training QA Reports to see line/field/pattern references."
        )
    records = _read_jsonl(path)
    examples, counts = _conversation_examples(records)
    if not examples:
        raise ValueError("No valid training conversations were found; export requires at least one user/assistant conversation.")
    jsonl_text = "".join(json.dumps(example, ensure_ascii=False, sort_keys=True) + "\n" for example in examples)
    summary = {
        "model_id": model,
        "file_format": "jsonl-chat-messages",
        "schema": '{"messages": [{"role": "user|assistant", "content": "..."}]}',
        "qa_status": qa_report.get("overall_status"),
        "qa_score": qa_report.get("scorecard", {}).get("overall_score"),
        "warnings": _warning_summary(qa_report),
    } | counts
    return PreparedTrainingExport(model_id=model, jsonl_text=jsonl_text, summary=summary, qa_report=qa_report)


def write_prepared_export(prepared: PreparedTrainingExport, output_path: Path | str) -> dict[str, Any]:
    out = Path(output_path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(prepared.jsonl_text, encoding="utf-8")
    return {"output_path": str(out), "bytes_written": out.stat().st_size, "summary": prepared.summary}


def _redact_sensitive_text(text: str) -> tuple[str, int]:
    redacted = text
    replacements = 0
    for name, pattern in SENSITIVE_PATTERNS.items():
        redacted, count = pattern.subn(f"[REDACTED_{name}]", redacted)
        replacements += count
    return redacted, replacements


def _redact_sensitive_values(value: Any) -> tuple[Any, int]:
    if isinstance(value, str):
        return _redact_sensitive_text(value)
    if isinstance(value, dict):
        fixed: dict[str, Any] = {}
        total = 0
        for key, item in value.items():
            fixed_item, count = _redact_sensitive_values(item)
            fixed[key] = fixed_item
            total += count
        return fixed, total
    if isinstance(value, list):
        fixed_items = []
        total = 0
        for item in value:
            fixed_item, count = _redact_sensitive_values(item)
            fixed_items.append(fixed_item)
            total += count
        return fixed_items, total
    return value, 0


def fix_export_blockers(log_path: Path | str = DEFAULT_LOG_PATH, timestamp: str | None = None) -> dict[str, Any]:
    """Safely auto-fix export-blocking data issues in a log.

    V1 fixes only deterministic blockers: sensitive strings are redacted and duplicate
    record_id values are regenerated. A full backup is created before rewriting.
    """
    log = Path(log_path).expanduser().resolve()
    if not log.exists():
        raise ValueError(f"Log path does not exist: {log}")
    stamp = timestamp or utc_stamp()
    backup_dir = log.parent / "fix-backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{log.stem}-before-fix-{stamp}{log.suffix or '.jsonl'}"
    shutil.copyfile(log, backup_path)

    seen_record_ids: set[str] = set()
    sensitive_replacements = 0
    duplicate_record_ids_fixed = 0
    fixed_lines: list[str] = []
    with backup_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except Exception as exc:
                raise ValueError(f"Cannot auto-fix invalid JSONL line {line_no}; fix the JSON syntax manually first: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"Cannot auto-fix invalid JSONL line {line_no}; top-level JSON value is not an object.")
            fixed_record, replacements = _redact_sensitive_values(record)
            sensitive_replacements += replacements
            record_id = fixed_record.get("record_id")
            if record_id:
                base = str(record_id)
                if base in seen_record_ids:
                    duplicate_record_ids_fixed += 1
                    candidate = f"{base}-dedup-{line_no}"
                    suffix = 2
                    while candidate in seen_record_ids:
                        candidate = f"{base}-dedup-{line_no}-{suffix}"
                        suffix += 1
                    fixed_record["record_id"] = candidate
                    seen_record_ids.add(candidate)
                else:
                    seen_record_ids.add(base)
            fixed_lines.append(json.dumps(fixed_record, ensure_ascii=False, sort_keys=True) + "\n")

    log.write_text("".join(fixed_lines), encoding="utf-8")
    after_report = analyze_log(log)
    return {
        "status": "fixed",
        "log_path": str(log),
        "backup_path": str(backup_path),
        "sensitive_replacements": sensitive_replacements,
        "duplicate_record_ids_fixed": duplicate_record_ids_fixed,
        "remaining_sensitive_findings": _sensitive_finding_count(after_report),
        "qa_status": after_report.get("overall_status"),
        "qa_score": after_report.get("scorecard", {}).get("overall_score"),
    }


def rotate_log_after_export(
    log_path: Path | str = DEFAULT_LOG_PATH,
    state_path: Path | str = DEFAULT_STATE_PATH,
    model_id: str = "",
    timestamp: str | None = None,
) -> dict[str, Any]:
    model = validate_model_id(model_id)
    log = Path(log_path).expanduser().resolve()
    state_file = Path(state_path).expanduser().resolve()
    stamp = timestamp or utc_stamp()
    archive_dir = log.parent / "exported-logs"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archived_log = archive_dir / f"ai-big-log-exported-{sanitize_model_id_for_filename(model)}-{stamp}.jsonl"
    if log.exists():
        shutil.copyfile(log, archived_log)
        log.write_text("", encoding="utf-8")
    else:
        archived_log.write_text("", encoding="utf-8")
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("", encoding="utf-8")

    state = load_state(state_file)
    state["export_rotation"] = {
        "rotated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model_id": model,
        "archived_log_path": str(archived_log),
        "new_log_path": str(log),
    }
    save_state(state_file, state)
    return state["export_rotation"]


def _previous_archive_candidates(state_path: Path | str, log_path: Path) -> list[Path]:
    state = load_state(Path(state_path).expanduser().resolve())
    candidates: list[Path] = []
    archived = (state.get("export_rotation") or {}).get("archived_log_path")
    if archived:
        candidates.append(Path(archived).expanduser().resolve())
    archive_dir = log_path.parent / "exported-logs"
    if archive_dir.exists():
        candidates.extend(sorted(archive_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True))
    seen: set[Path] = set()
    usable: list[Path] = []
    for candidate in candidates:
        if candidate in seen or candidate == log_path:
            continue
        seen.add(candidate)
        if candidate.exists() and candidate.stat().st_size > 0:
            usable.append(candidate)
    return usable


def _usable_previous_archive(state_path: Path | str, log_path: Path) -> Path | None:
    candidates = _previous_archive_candidates(state_path, log_path)
    return candidates[0] if candidates else None


def run_export(
    log_path: Path | str,
    model_id: str,
    output_path: Path | str | None = None,
    rotate: bool = False,
    state_path: Path | str = DEFAULT_STATE_PATH,
    start_new_log_first: bool = False,
) -> dict[str, Any]:
    source_log_path = Path(log_path).expanduser().resolve()
    rotation = None
    prepared = None
    last_prepare_error: Exception | None = None
    if start_new_log_first:
        if source_log_path.exists() and source_log_path.stat().st_size > 0:
            rotation = rotate_log_after_export(source_log_path, state_path, model_id)
            source_log_path = Path(rotation["archived_log_path"])
        else:
            for candidate in _previous_archive_candidates(state_path, source_log_path):
                try:
                    prepared = prepare_training_export(candidate, model_id)
                    source_log_path = candidate
                    break
                except Exception as exc:
                    last_prepare_error = exc
                    if "Sensitive data was caught" in str(exc):
                        source_log_path = candidate
                        break
    if prepared is None:
        try:
            prepared = prepare_training_export(source_log_path, model_id)
        except Exception as exc:
            if rotation or start_new_log_first:
                return {
                    "status": "error",
                    "error": str(exc),
                    "source_log_path": str(source_log_path),
                    **({"rotation": rotation} if rotation else {}),
                }
            raise
    result: dict[str, Any] = {
        "status": "prepared",
        "summary": prepared.summary,
        "source_log_path": str(source_log_path),
    }
    if rotation:
        result["rotation"] = rotation
    if output_path:
        result.update(write_prepared_export(prepared, output_path))
        result["status"] = "exported"
        if rotate and not start_new_log_first:
            result["rotation"] = rotate_log_after_export(log_path, state_path, model_id)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare/export ai-big-log training data as conversational JSONL.")
    parser.add_argument("--log-path", default=str(DEFAULT_LOG_PATH))
    parser.add_argument("--state-path", default=str(DEFAULT_STATE_PATH))
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--output-path")
    parser.add_argument("--start-new-log-first", action="store_true", help="Archive/reset the active log before prepare so UI/export activity logs to a fresh active log.")
    parser.add_argument("--fix-export-blockers", action="store_true", help="Back up the selected log, redact sensitive strings, and regenerate duplicate record IDs.")
    parser.add_argument("--rotate-after-export", action="store_true", help="Archive/reset the active log after a successful export write.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.fix_export_blockers:
            result = fix_export_blockers(args.log_path)
        else:
            result = run_export(args.log_path, args.model_id, args.output_path, args.rotate_after_export, args.state_path, args.start_new_log_first)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result.get("status") == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
