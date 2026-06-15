from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = PROJECT_ROOT / "logs"
DEFAULT_LOG_PATH = DEFAULT_LOG_DIR / "ai-big-log.jsonl"
DEFAULT_SUMMARY_PATH = DEFAULT_LOG_DIR / "ai-big-log-summary.md"
DEFAULT_STATE_PATH = DEFAULT_LOG_DIR / "state.json"
DEFAULT_OPERATIONAL_LOG_PATH = DEFAULT_LOG_DIR / "operations.jsonl"
DEFAULT_WORKSPACE = Path.home() / "workspace"
DEFAULT_AI_HOME = Path.home() / ".ai"
DEFAULT_STATE_DB = DEFAULT_AI_HOME / "state.db"

DEFAULT_CONFIG: dict[str, Any] = {
    "workspace_root": str(DEFAULT_WORKSPACE),
    "ai_home": str(DEFAULT_AI_HOME),
    "state_db": str(DEFAULT_STATE_DB),
    "log_path": str(DEFAULT_LOG_PATH),
    "summary_path": str(DEFAULT_SUMMARY_PATH),
    "state_path": str(DEFAULT_STATE_PATH),
    "operational_log_path": str(DEFAULT_OPERATIONAL_LOG_PATH),
    "noisy_dirs": [
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        "target",
        ".cache",
    ],
    "sensitive_names": [
        ".env",
        ".env.local",
        ".envrc",
        "id_rsa",
        "id_ed25519",
        "auth.json",
        ".netrc",
    ],
    "text_extensions": [
        ".txt",
        ".md",
        ".py",
        ".json",
        ".jsonl",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".sh",
        ".bash",
        ".js",
        ".ts",
        ".html",
        ".css",
        ".csv",
        ".xml",
        ".kcl",
    ],
    "max_text_bytes": 512_000,
}

SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9_\-]{6,}"), "[REDACTED_SECRET]"),
    (re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,'\"]+"), r"\1=[REDACTED_SECRET]"),
    (re.compile(r"\*\*\*+"), "[REDACTED_SECRET]"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "[REDACTED_PRIVATE_KEY]"),
]
PII_PATTERNS = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    (re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b"), "[REDACTED_PHONE]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
    (re.compile(r"\b(?:\d[ -]*?){13,16}\b"), "[REDACTED_FINANCIAL_NUMBER]"),
]


class Redactor:
    def __init__(self) -> None:
        self.patterns = SECRET_PATTERNS + PII_PATTERNS

    def redact(self, value: Any) -> tuple[Any, int]:
        if value is None:
            return None, 0
        if isinstance(value, str):
            text = value
            count = 0
            for pattern, repl in self.patterns:
                text, n = pattern.subn(repl, text)
                count += n
            return text, count
        if isinstance(value, list):
            out = []
            total = 0
            for item in value:
                redacted, count = self.redact(item)
                out.append(redacted)
                total += count
            return out, total
        if isinstance(value, dict):
            out = {}
            total = 0
            for key, item in value.items():
                redacted, count = self.redact(item)
                out[key] = redacted
                total += count
            return out, total
        return value, 0


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_state(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"seen_message_ids": [], "files": {}, "runs": []}
    return json.loads(p.read_text(encoding="utf-8"))


def save_state(path: Path | str, state: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f"{p.name}.{os.getpid()}.{time.time_ns()}.tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(p)


def append_jsonl(path: Path | str, records: Iterable[dict[str, Any]]) -> int:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with p.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def parse_jsonish(value: Any) -> Any:
    if not value or not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except Exception:
        return value


def collect_session_records(state_db: Path | str, redactor: Redactor, seen_message_ids: set[int]) -> Iterable[dict[str, Any]]:
    db = Path(state_db)
    if not db.exists():
        return []
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    min_message_id = max(seen_message_ids) if seen_message_ids else 0
    query = """
        select
            m.id as message_id, m.session_id, m.role, m.content, m.tool_call_id, m.tool_calls,
            m.tool_name, m.timestamp, m.token_count, m.finish_reason, m.platform_message_id,
            s.source, s.model, s.model_config, s.started_at, s.ended_at, s.end_reason,
            s.message_count, s.tool_call_count, s.cwd, s.title
        from messages m
        join sessions s on s.id = m.session_id
        where coalesce(m.active, 1) = 1
          and m.id > ?
        order by m.id asc
    """
    rows = con.execute(query, (min_message_id,)).fetchall()
    con.close()
    out = []
    for row in rows:
        mid = int(row["message_id"])
        if mid in seen_message_ids:
            continue
        tool_calls = parse_jsonish(row["tool_calls"])
        content, c1 = redactor.redact(row["content"])
        tool_calls, c2 = redactor.redact(tool_calls)
        model_config, c3 = redactor.redact(parse_jsonish(row["model_config"]))
        record = {
            "record_id": f"ai-message-{mid}",
            "record_type": "ai_message",
            "captured_at": utc_now_iso(),
            "message_id": mid,
            "session_id": row["session_id"],
            "session_title": row["title"],
            "session_source": row["source"],
            "session_started_at": row["started_at"],
            "session_ended_at": row["ended_at"],
            "session_end_reason": row["end_reason"],
            "role": row["role"],
            "content": content,
            "tool_call_id": row["tool_call_id"],
            "tool_calls": tool_calls,
            "tool_name": row["tool_name"],
            "timestamp": row["timestamp"],
            "token_count": row["token_count"],
            "finish_reason": row["finish_reason"],
            "platform_message_id": row["platform_message_id"],
            "model": row["model"],
            "model_config": model_config,
            "working_directory": row["cwd"],
            "session_message_count": row["message_count"],
            "session_tool_call_count": row["tool_call_count"],
            "redaction_count": c1 + c2 + c3,
        }
        out.append(record)
    return out


def is_noisy_dir(path: Path, config: dict[str, Any]) -> bool:
    return path.name in set(config.get("noisy_dirs", []))


def is_sensitive_name(path: Path, config: dict[str, Any]) -> bool:
    return path.name in set(config.get("sensitive_names", []))


def is_allowed_text(path: Path, config: dict[str, Any]) -> bool:
    if is_sensitive_name(path, config):
        return False
    if path.suffix.lower() not in set(config.get("text_extensions", [])):
        return False
    try:
        if path.stat().st_size > int(config.get("max_text_bytes", 512_000)):
            return False
        path.read_text(encoding="utf-8")
        return True
    except Exception:
        return False


def relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def collect_file_events(workspace_root: Path | str, state: dict[str, Any], redactor: Redactor, config: dict[str, Any]) -> Iterable[dict[str, Any]]:
    root = Path(workspace_root).expanduser().resolve()
    files_state = state.setdefault("files", {})
    seen_folders = state.setdefault("seen_folder_records", {})
    now = utc_now_iso()
    records: list[dict[str, Any]] = []
    if not root.exists():
        return [{"record_id": f"workspace-missing-{stable_hash(str(root))}", "record_type": "logger_error", "captured_at": now, "path": str(root), "error": "workspace root does not exist"}]

    for current_root, dirnames, filenames in os.walk(root):
        current = Path(current_root)
        noisy_children = [d for d in list(dirnames) if d in set(config.get("noisy_dirs", []))]
        for dirname in noisy_children:
            dpath = current / dirname
            try:
                stat = dpath.stat()
                rid = f"folder-{stable_hash(str(dpath))}-{int(stat.st_mtime)}"
                # Dedup: only emit a folder_metadata record when path+mtime
                # changed since last run, so unchanged noisy folders don't
                # re-append identical records every 15 minutes.
                if seen_folders.get(str(dpath)) == rid:
                    continue
                seen_folders[str(dpath)] = rid
                records.append({
                    "record_id": rid,
                    "record_type": "folder_metadata",
                    "captured_at": now,
                    "path": str(dpath),
                    "relative_path": relative(dpath, root),
                    "folder_name": dirname,
                    "policy": "metadata_only_noisy_folder",
                    "mtime": stat.st_mtime,
                })
            except Exception as exc:
                records.append({"record_id": f"folder-error-{stable_hash(str(dpath)+str(time.time()))}", "record_type": "logger_error", "captured_at": now, "path": str(dpath), "error": str(exc)})
        dirnames[:] = [d for d in dirnames if d not in set(config.get("noisy_dirs", []))]

        for filename in filenames:
            path = current / filename
            try:
                stat = path.stat()
                key = str(path)
                digest = file_hash(path)
                prev = files_state.get(key)
                if prev and prev.get("hash") == digest and prev.get("size") == stat.st_size:
                    continue
                event = "created" if not prev else "modified"
                record: dict[str, Any] = {
                    "record_id": f"file-{stable_hash(key + digest)}",
                    "record_type": "file_event",
                    "captured_at": now,
                    "event": event,
                    "path": key,
                    "relative_path": relative(path, root),
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                    "sha256": digest,
                    "content_policy": "metadata_only",
                }
                if is_allowed_text(path, config):
                    new_text = path.read_text(encoding="utf-8")
                    new_text_redacted, count = redactor.redact(new_text)
                    old_text = prev.get("text") if prev else ""
                    diff = "".join(difflib.unified_diff(
                        (old_text or "").splitlines(keepends=True),
                        str(new_text_redacted).splitlines(keepends=True),
                        fromfile=f"before/{relative(path, root)}",
                        tofile=f"after/{relative(path, root)}",
                    ))
                    record.update({"content_policy": "redacted_safe_diff", "safe_diff": diff, "redaction_count": count})
                    files_state[key] = {"hash": digest, "size": stat.st_size, "mtime": stat.st_mtime, "text": new_text_redacted}
                else:
                    record.update({"skip_reason": "binary_or_sensitive_or_unsupported_text"})
                    files_state[key] = {"hash": digest, "size": stat.st_size, "mtime": stat.st_mtime}
                records.append(record)
            except Exception as exc:
                records.append({"record_id": f"file-error-{stable_hash(str(path)+str(time.time()))}", "record_type": "logger_error", "captured_at": now, "path": str(path), "error": str(exc)})
    return records


def collect_external_log_records(source_path: Path | str, state: dict[str, Any], redactor: Redactor, source_name: str | None = None) -> list[dict[str, Any]]:
    """Deterministically import new lines from an external append-only log.

    This intentionally does not shell out to `cat`. It tracks how many lines were
    already imported per source path, wraps each new source line in a BigLog
    record, redacts content, and gives every imported line a stable record_id.
    """
    path = Path(source_path).expanduser().resolve()
    now = utc_now_iso()
    if not path.exists():
        return [{
            "record_id": f"external-log-missing-{stable_hash(str(path))}",
            "record_type": "logger_error",
            "captured_at": now,
            "source": "external_log",
            "path": str(path),
            "error": "external log file does not exist",
        }]
    if not path.is_file():
        return [{
            "record_id": f"external-log-not-file-{stable_hash(str(path))}",
            "record_type": "logger_error",
            "captured_at": now,
            "source": "external_log",
            "path": str(path),
            "error": "external log path is not a file",
        }]

    external_state = state.setdefault("external_logs", {})
    key = str(path)
    previous = external_state.setdefault(key, {"line_count": 0})
    previous_line_count = int(previous.get("line_count", 0) or 0)
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    records: list[dict[str, Any]] = []

    if len(lines) < previous_line_count:
        records.append({
            "record_id": f"external-log-rotated-{stable_hash(key + str(time.time_ns()))}",
            "record_type": "logger_operation",
            "captured_at": now,
            "operation": "external_log_rotated_or_truncated",
            "source_path": key,
            "previous_line_count": previous_line_count,
            "current_line_count": len(lines),
        })
        previous_line_count = 0

    for line_number, line in enumerate(lines[previous_line_count:], previous_line_count + 1):
        redacted_line, redaction_count = redactor.redact(line)
        line_hash = stable_hash(str(redacted_line))
        records.append({
            "record_id": f"external-log-{stable_hash(key + ':' + str(line_number) + ':' + line_hash)}",
            "record_type": "external_log_line",
            "captured_at": now,
            "source_name": source_name or path.stem,
            "source_path": key,
            "source_line_number": line_number,
            "source_line_sha256": line_hash,
            "content": redacted_line,
            "redaction_count": redaction_count,
        })

    previous.update({
        "line_count": len(lines),
        "updated_at": now,
        "source_name": source_name or path.stem,
        "size": path.stat().st_size,
        "mtime": path.stat().st_mtime,
    })
    return records


def run_ingest_log(config: dict[str, Any], source_path: Path | str, source_name: str | None = None) -> dict[str, Any]:
    started = utc_now_iso()
    redactor = Redactor()
    state_path = Path(config["state_path"])
    state = load_state(state_path)
    records = collect_external_log_records(source_path, state, redactor, source_name=source_name)
    errors = sum(1 for record in records if record.get("record_type") == "logger_error")
    appended = append_jsonl(Path(config["log_path"]), records)
    run = {
        "started_at": started,
        "ended_at": utc_now_iso(),
        "status": "ok" if errors == 0 else "completed_with_errors",
        "records_appended": appended,
        "errors": errors,
        "operation": "ingest_log",
        "source_path": str(Path(source_path).expanduser()),
    }
    state.setdefault("runs", []).append(run)
    state["last_run"] = run
    save_state(state_path, state)
    append_jsonl(Path(config["operational_log_path"]), [{"record_id": f"operation-{stable_hash(json.dumps(run, sort_keys=True))}", "record_type": "operation", **run}])
    validation = validate_log(Path(config["log_path"]))
    write_summary(Path(config["summary_path"]), Path(config["log_path"]), state, validation, run)
    return run | {"validation": validation}


def validate_log(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    result = {"valid": True, "records": 0, "errors": []}
    if not p.exists():
        result["valid"] = False
        result["errors"].append("log file does not exist")
        return result
    with p.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                if "record_id" not in obj or "record_type" not in obj:
                    raise ValueError("missing record_id or record_type")
                result["records"] += 1
            except Exception as exc:
                result["valid"] = False
                result["errors"].append(f"line {idx}: {exc}")
    return result


def write_summary(path: Path | str, log_path: Path | str, state: dict[str, Any], validation: dict[str, Any], last_run: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    content = f"""# AI Big Log Summary

Last updated: {utc_now_iso()}

Main log: `{Path(log_path)}`

## Current status

- Valid JSONL: {validation.get('valid')}
- Total JSONL records: {validation.get('records')}
- Seen AI message IDs: {len(state.get('seen_message_ids', []))}
- Tracked workspace files: {len(state.get('files', {}))}
- Last run status: {last_run.get('status', 'unknown')}
- Last run records appended: {last_run.get('records_appended', 0)}
- Last run errors: {last_run.get('errors', 0)}

## Notes

This is a logging-only source record. It is not a training export pipeline.
Sensitive data is redacted before records are appended when detected by the MVP redaction rules.
"""
    p.write_text(content, encoding="utf-8")


def run_update(config: dict[str, Any]) -> dict[str, Any]:
    started = utc_now_iso()
    redactor = Redactor()
    state_path = Path(config["state_path"])
    state = load_state(state_path)
    seen = {int(x) for x in state.get("seen_message_ids", [])}
    records: list[dict[str, Any]] = []
    errors = 0

    try:
        session_records = list(collect_session_records(Path(config["state_db"]), redactor, seen))
        records.extend(session_records)
        for record in session_records:
            seen.add(int(record["message_id"]))
    except Exception as exc:
        errors += 1
        records.append({"record_id": f"logger-error-session-{stable_hash(str(exc)+str(time.time()))}", "record_type": "logger_error", "captured_at": utc_now_iso(), "source": "sessions", "error": str(exc)})

    if config.get("skip_file_scan"):
        records.append({
            "record_id": f"file-scan-skipped-{stable_hash(started)}",
            "record_type": "logger_operation",
            "captured_at": utc_now_iso(),
            "operation": "file_scan_skipped",
            "reason": "fast session-capture cron run",
        })
    else:
        try:
            records.extend(collect_file_events(Path(config["workspace_root"]), state, redactor, config))
        except Exception as exc:
            errors += 1
            records.append({"record_id": f"logger-error-files-{stable_hash(str(exc)+str(time.time()))}", "record_type": "logger_error", "captured_at": utc_now_iso(), "source": "files", "error": str(exc)})

    appended = append_jsonl(Path(config["log_path"]), records)
    state["seen_message_ids"] = sorted(seen)
    run = {"started_at": started, "ended_at": utc_now_iso(), "status": "ok" if errors == 0 else "completed_with_errors", "records_appended": appended, "errors": errors}
    state.setdefault("runs", []).append(run)
    state["last_run"] = run
    save_state(state_path, state)
    append_jsonl(Path(config["operational_log_path"]), [{"record_id": f"operation-{stable_hash(json.dumps(run, sort_keys=True))}", "record_type": "operation", **run}])
    validation = validate_log(Path(config["log_path"]))
    write_summary(Path(config["summary_path"]), Path(config["log_path"]), state, validation, run)
    return run | {"validation": validation}


def run_status(config: dict[str, Any]) -> dict[str, Any]:
    state = load_state(Path(config["state_path"]))
    validation = validate_log(Path(config["log_path"])) if Path(config["log_path"]).exists() else {"valid": False, "records": 0, "errors": ["log missing"]}
    return {
        "log_path": config["log_path"],
        "summary_path": config["summary_path"],
        "state_path": config["state_path"],
        "seen_message_ids": len(state.get("seen_message_ids", [])),
        "tracked_files": len(state.get("files", {})),
        "last_run": state.get("last_run"),
        "validation": validation,
    }


def run_health(config: dict[str, Any], max_stale_minutes: int = 45) -> dict[str, Any]:
    state = load_state(Path(config["state_path"]))
    validation = validate_log(Path(config["log_path"])) if Path(config["log_path"]).exists() else {"valid": False, "records": 0, "errors": ["log missing"]}
    last_run = state.get("last_run") or {}
    issues: list[str] = []
    if not validation.get("valid"):
        issues.append("BigLog JSONL validation failed")
    ended_at = last_run.get("ended_at")
    age_minutes = None
    if not ended_at:
        issues.append("BigLog has no recorded last_run")
    else:
        try:
            ended = datetime.fromisoformat(str(ended_at))
            age_minutes = (datetime.now(timezone.utc) - ended).total_seconds() / 60
            if age_minutes > max_stale_minutes:
                issues.append(f"BigLog last run is stale: {age_minutes:.1f} minutes old")
        except Exception as exc:
            issues.append(f"BigLog last_run timestamp is unreadable: {exc}")
    if last_run.get("status") not in ("ok", None):
        issues.append(f"BigLog last_run status is {last_run.get('status')}")
    if int(last_run.get("errors", 0) or 0) != 0:
        issues.append(f"BigLog last_run errors={last_run.get('errors')}")
    return {
        "healthy": not issues,
        "issues": issues,
        "max_stale_minutes": max_stale_minutes,
        "last_run_age_minutes": age_minutes,
        "last_run": last_run,
        "log_path": config["log_path"],
        "validation": validation,
        "seen_message_ids": len(state.get("seen_message_ids", [])),
    }


def print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def _add_common_options(p: argparse.ArgumentParser) -> None:
    p.add_argument("--workspace-root", default=DEFAULT_CONFIG["workspace_root"])
    p.add_argument("--state-db", default=DEFAULT_CONFIG["state_db"])
    p.add_argument("--log-path", default=DEFAULT_CONFIG["log_path"])
    p.add_argument("--summary-path", default=DEFAULT_CONFIG["summary_path"])
    p.add_argument("--state-path", default=DEFAULT_CONFIG["state_path"])
    p.add_argument("--operational-log-path", default=DEFAULT_CONFIG["operational_log_path"])
    p.add_argument("--skip-file-scan", action="store_true", help="Capture AI session messages only; skip slow workspace scan")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Project-local AI Big Log MVP")
    # Allow options either before OR after the subcommand: register on the
    # top-level parser and on each subparser via a shared parent.
    _add_common_options(parser)
    common = argparse.ArgumentParser(add_help=False)
    _add_common_options(common)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("update", parents=[common], help="Append new AI conversation records and workspace changes")
    sub.add_parser("status", parents=[common], help="Show logger status")
    health = sub.add_parser("health", parents=[common], help="Fail loudly if BigLog is invalid or stale")
    health.add_argument("--max-stale-minutes", type=int, default=45)
    ingest = sub.add_parser("ingest-log", parents=[common], help="Deterministically import new lines from an external append-only log")
    ingest.add_argument("source_path")
    ingest.add_argument("--source-name", default=None)
    sub.add_parser("validate", parents=[common], help="Validate the append-only JSONL log")
    qa = sub.add_parser("training-qa-report", parents=[common], help="Analyze the log for training-data QA and write Markdown/JSON reports")
    qa.add_argument("--report-dir", default=str(PROJECT_ROOT / "reports"))
    sub.add_parser("cron-prompt", parents=[common], help="Print a self-contained prompt/command for scheduled cron setup")
    return parser


def config_from_args(args: argparse.Namespace) -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    for key in ["workspace_root", "state_db", "log_path", "summary_path", "state_path", "operational_log_path", "skip_file_scan"]:
        config[key] = getattr(args, key)
    return config


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = config_from_args(args)
    if args.command == "update":
        print_json(run_update(config))
        return 0
    if args.command == "status":
        print_json(run_status(config))
        return 0
    if args.command == "health":
        result = run_health(config, max_stale_minutes=args.max_stale_minutes)
        print_json(result)
        return 0 if result.get("healthy") else 1
    if args.command == "ingest-log":
        result = run_ingest_log(config, args.source_path, source_name=args.source_name)
        print_json(result)
        return 0 if result.get("status") == "ok" and result.get("validation", {}).get("valid") else 1
    if args.command == "validate":
        result = validate_log(Path(config["log_path"]))
        print_json(result)
        return 0 if result.get("valid") else 1
    if args.command == "training-qa-report":
        from ai_big_log.training_qa import run_training_qa
        result = run_training_qa(Path(config["log_path"]), args.report_dir)
        print_json(result)
        return 0 if result.get("status") in {"pass", "warn"} else 1
    if args.command == "cron-prompt":
        script = PROJECT_ROOT / "ai-big-log"
        print(f"Run this every 15 minutes from scheduled cron: {script} update")
        return 0
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
