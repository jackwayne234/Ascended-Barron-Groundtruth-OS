from __future__ import annotations

import argparse
import collections
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_PATH = PROJECT_ROOT / "logs" / "ai-big-log.jsonl"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "reports"

EXPECTED_REQUIRED_FIELDS: dict[str, list[str]] = {
    "ai_message": [
        "record_id", "record_type", "captured_at", "message_id", "session_id",
        "role", "timestamp", "redaction_count",
    ],
    "file_event": [
        "record_id", "record_type", "captured_at", "event", "path", "relative_path",
        "size", "mtime", "sha256", "content_policy",
    ],
    "folder_metadata": [
        "record_id", "record_type", "captured_at", "path", "relative_path",
        "folder_name", "policy", "mtime",
    ],
    "dashboard_event": [
        "record_id", "record_type", "captured_at", "session", "kind", "action",
    ],
    "logger_operation": ["record_id", "record_type", "captured_at", "operation"],
    "logger_error": ["record_id", "record_type", "captured_at", "error"],
    "operation": ["record_id", "record_type", "started_at", "ended_at", "status"],
    "external_log_line": [
        "record_id", "record_type", "captured_at", "source_path", "source_line_number",
        "source_line_sha256", "content",
    ],
}

SENSITIVE_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "financial_number": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "secret_token": re.compile(r"(?i)sk-[A-Za-z0-9_\-]{6,}|(api[_-]?key|token|password|secret|bearer)\s*[:=]"),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_time(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except Exception:
            return None
    return None


def _walk_strings(value: Any, prefix: str = ""):
    if isinstance(value, str):
        yield prefix or "$", value
    elif isinstance(value, dict):
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            yield from _walk_strings(item, child)
    elif isinstance(value, list):
        for idx, item in enumerate(value[:100]):
            child = f"{prefix}[{idx}]" if prefix else f"[{idx}]"
            yield from _walk_strings(item, child)


def _sample(counter_or_items, limit: int = 10):
    if hasattr(counter_or_items, "most_common"):
        return counter_or_items.most_common(limit)
    return list(counter_or_items)[:limit]


def analyze_log(log_path: Path | str = DEFAULT_LOG_PATH) -> dict[str, Any]:
    path = Path(log_path).expanduser().resolve()
    result: dict[str, Any] = {
        "generated_at": utc_now_iso(),
        "log_path": str(path),
        "valid_jsonl": True,
        "readable": True,
        "line_count": 0,
        "empty_lines": 0,
        "invalid_json_lines": [],
        "record_type_counts": {},
        "schema_missing_required": {},
        "unknown_record_types": {},
        "duplicate_record_ids": {"count": 0, "samples": []},
        "message_id_gaps": [],
        "timestamp_backsteps": [],
        "logger_errors": {"count": 0, "samples": []},
        "sensitive_findings": {"count": 0, "by_pattern": {}, "samples": []},
        "empty_or_null_content": {},
        "coverage": {},
        "scorecard": {},
        "overall_status": "fail",
        "recommended_fixes": [],
    }
    if not path.exists():
        result["readable"] = False
        result["valid_jsonl"] = False
        result["recommended_fixes"].append("Confirm the ai-big-log path exists before running QA.")
        _score(result)
        return result

    record_type_counts = collections.Counter()
    missing_required = collections.Counter()
    unknown_record_types = collections.Counter()
    first_record_line: dict[str, int] = {}
    dup_samples: list[dict[str, Any]] = []
    role_counts = collections.Counter()
    session_sources = collections.Counter()
    dashboard_kinds = collections.Counter()
    dashboard_actions = collections.Counter()
    file_events = collections.Counter()
    file_policies = collections.Counter()
    logger_error_samples: list[dict[str, Any]] = []
    sensitive_by_pattern = collections.Counter()
    sensitive_samples: list[dict[str, Any]] = []
    empty_or_null_content = collections.Counter()
    message_ids: list[int] = []
    previous_message_ts: float | None = None
    previous_captured_ts: float | None = None
    timestamp_backsteps: list[dict[str, Any]] = []
    redacted_records = 0
    sessions = set()
    max_line_length = 0

    try:
        with path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                result["line_count"] = line_no
                max_line_length = max(max_line_length, len(line.encode("utf-8", errors="replace")))
                if not line.strip():
                    result["empty_lines"] += 1
                    continue
                try:
                    obj = json.loads(line)
                except Exception as exc:
                    result["valid_jsonl"] = False
                    if len(result["invalid_json_lines"]) < 25:
                        result["invalid_json_lines"].append({"line": line_no, "error": str(exc)})
                    continue
                if not isinstance(obj, dict):
                    result["valid_jsonl"] = False
                    if len(result["invalid_json_lines"]) < 25:
                        result["invalid_json_lines"].append({"line": line_no, "error": "top-level JSON value is not an object"})
                    continue

                record_type = str(obj.get("record_type", "<missing>"))
                record_type_counts[record_type] += 1
                expected = EXPECTED_REQUIRED_FIELDS.get(record_type)
                if expected is None:
                    unknown_record_types[record_type] += 1
                    expected = ["record_id", "record_type", "captured_at"]
                for field in expected:
                    if field not in obj:
                        missing_required[(record_type, field)] += 1

                record_id = obj.get("record_id")
                if record_id:
                    rid = str(record_id)
                    if rid in first_record_line:
                        if len(dup_samples) < 100:
                            dup_samples.append({"record_id": rid, "first_line": first_record_line[rid], "duplicate_line": line_no})
                    else:
                        first_record_line[rid] = line_no

                captured_ts = _parse_time(obj.get("captured_at"))
                if captured_ts is not None:
                    if previous_captured_ts is not None and captured_ts < previous_captured_ts and len(timestamp_backsteps) < 50:
                        timestamp_backsteps.append({"scope": "captured_at", "line": line_no})
                    previous_captured_ts = captured_ts

                for field_path, text in _walk_strings(obj):
                    for name, pattern in SENSITIVE_PATTERNS.items():
                        if pattern.search(text):
                            sensitive_by_pattern[name] += 1
                            if len(sensitive_samples) < 100:
                                sensitive_samples.append({"line": line_no, "field": field_path, "pattern": name})

                if int(obj.get("redaction_count") or 0) > 0:
                    redacted_records += 1

                if record_type == "ai_message":
                    role = str(obj.get("role"))
                    role_counts[role] += 1
                    session_sources[str(obj.get("session_source"))] += 1
                    if obj.get("session_id") is not None:
                        sessions.add(str(obj.get("session_id")))
                    if isinstance(obj.get("message_id"), int):
                        message_ids.append(int(obj["message_id"]))
                    content = obj.get("content")
                    if content is None:
                        empty_or_null_content[f"{role}:null"] += 1
                    elif content == "":
                        empty_or_null_content[f"{role}:empty"] += 1
                    ts = _parse_time(obj.get("timestamp"))
                    if ts is not None:
                        if previous_message_ts is not None and ts < previous_message_ts and len(timestamp_backsteps) < 50:
                            timestamp_backsteps.append({"scope": "ai_message.timestamp", "line": line_no})
                        previous_message_ts = ts
                elif record_type == "dashboard_event":
                    dashboard_kinds[str(obj.get("kind"))] += 1
                    dashboard_actions[str(obj.get("action"))] += 1
                elif record_type == "file_event":
                    file_events[str(obj.get("event"))] += 1
                    file_policies[str(obj.get("content_policy"))] += 1
                elif record_type == "logger_error":
                    if len(logger_error_samples) < 25:
                        logger_error_samples.append({
                            "line": line_no,
                            "source": obj.get("source"),
                            "path": obj.get("path"),
                            "error_type": type(obj.get("error")).__name__,
                        })
    except Exception as exc:
        result["readable"] = False
        result["valid_jsonl"] = False
        result["read_error"] = str(exc)

    duplicate_count = sum(1 for _ in dup_samples)
    if len(dup_samples) == 100:
        duplicate_count = max(duplicate_count, result["line_count"] - len(first_record_line))
    if message_ids:
        sorted_ids = sorted(set(message_ids))
        for a, b in zip(sorted_ids, sorted_ids[1:]):
            if b > a + 1 and len(result["message_id_gaps"]) < 100:
                result["message_id_gaps"].append({"after": a, "before": b, "missing_count": b - a - 1})

    result.update({
        "file_size_bytes": path.stat().st_size if path.exists() else 0,
        "max_line_length_bytes": max_line_length,
        "record_type_counts": dict(record_type_counts),
        "schema_missing_required": {f"{rt}.{field}": count for (rt, field), count in missing_required.items()},
        "unknown_record_types": dict(unknown_record_types),
        "duplicate_record_ids": {"count": duplicate_count, "samples": dup_samples},
        "timestamp_backsteps": timestamp_backsteps,
        "logger_errors": {"count": record_type_counts.get("logger_error", 0), "samples": logger_error_samples},
        "sensitive_findings": {
            "count": sum(sensitive_by_pattern.values()),
            "by_pattern": dict(sensitive_by_pattern),
            "samples": sensitive_samples,
        },
        "empty_or_null_content": dict(empty_or_null_content),
        "coverage": {
            "ai_roles": dict(role_counts),
            "ai_sessions": len(sessions),
            "session_sources": dict(session_sources),
            "dashboard_kinds": dict(dashboard_kinds),
            "dashboard_actions_top": dashboard_actions.most_common(25),
            "file_events": dict(file_events),
            "file_content_policies": dict(file_policies),
            "redacted_records": redacted_records,
            "message_id_range": [min(message_ids), max(message_ids)] if message_ids else None,
            "unique_message_ids": len(set(message_ids)),
        },
    })
    _score(result)
    return result


def _score(result: dict[str, Any]) -> None:
    validity = 100 if result.get("readable") and result.get("valid_jsonl") and not result.get("empty_lines") else 0
    schema_missing = sum(result.get("schema_missing_required", {}).values())
    schema = 100 if schema_missing == 0 else max(0, 100 - schema_missing * 10)
    duplicate_count = int(result.get("duplicate_record_ids", {}).get("count", 0) or 0)
    uniqueness = 100 if duplicate_count == 0 else max(60, 100 - min(40, duplicate_count))
    sensitive_count = int(result.get("sensitive_findings", {}).get("count", 0) or 0)
    privacy = 100 if sensitive_count == 0 else max(40, 100 - min(60, sensitive_count // 5 + 10))
    chronology = 100 if not result.get("timestamp_backsteps") and not result.get("message_id_gaps") else 80
    coverage = 100
    required_types = {"ai_message", "file_event", "dashboard_event", "logger_operation"}
    present_types = set(result.get("record_type_counts", {}))
    missing_types = sorted(required_types - present_types)
    if missing_types:
        coverage -= 15 * len(missing_types)

    scorecard = {
        "validity": validity,
        "schema": schema,
        "uniqueness": uniqueness,
        "privacy": privacy,
        "chronology": chronology,
        "coverage": max(0, coverage),
    }
    overall_score = round(sum(scorecard.values()) / len(scorecard), 1)
    if not result.get("readable") or not result.get("valid_jsonl"):
        status = "fail"
    elif schema < 90 or privacy < 90 or duplicate_count or result.get("logger_errors", {}).get("count", 0) or result.get("timestamp_backsteps"):
        status = "warn"
    else:
        status = "pass"
    result["scorecard"] = scorecard | {"overall_score": overall_score}
    result["overall_status"] = status

    fixes = []
    if duplicate_count:
        fixes.append("Investigate duplicate record_id generation/state replay; keep record_id unique across backfills and reruns.")
    if result.get("logger_errors", {}).get("count", 0):
        fixes.append("Review logger_error samples and make workspace file scanning tolerate deleted symlink targets and changing ISO-build paths.")
    if sensitive_count:
        fixes.append("Expand redaction rules or review flagged fields; reports intentionally show line/field/pattern only, not raw values.")
    if result.get("timestamp_backsteps"):
        fixes.append("Check append order/backfill behavior for timestamp backsteps; consider sorting exports by event timestamp for training datasets.")
    if result.get("message_id_gaps"):
        fixes.append("Confirm message_id gaps are expected inactive/deleted messages; otherwise backfill missing active messages.")
    if schema_missing:
        fixes.append("Update logger emitters or QA schema so every expected record type includes required fields.")
    if missing_types:
        fixes.append(f"Missing expected record types in this log: {', '.join(missing_types)}.")
    if not fixes and status == "pass":
        fixes.append("No critical fixes found; keep running periodic QA before using logs as training data.")
    result["recommended_fixes"] = fixes


def _markdown_table(rows: list[list[Any]], headers: list[str]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(x).replace("|", "\\|") for x in row) + " |")
    return "\n".join(out)


def render_markdown(report: dict[str, Any]) -> str:
    score = report.get("scorecard", {})
    findings = []
    if not report.get("valid_jsonl"):
        findings.append(["FAIL", "JSONL validity", len(report.get("invalid_json_lines", [])), "Fix invalid JSON lines before training use."])
    if report.get("schema_missing_required"):
        findings.append(["WARN", "Missing required fields", sum(report["schema_missing_required"].values()), "Update logger/schema."])
    dup_count = report.get("duplicate_record_ids", {}).get("count", 0)
    if dup_count:
        findings.append(["WARN", "Duplicate record_id", dup_count, "Investigate replay/state handling."])
    if report.get("logger_errors", {}).get("count", 0):
        findings.append(["WARN", "logger_error records", report["logger_errors"]["count"], "Review scanner errors."])
    if report.get("sensitive_findings", {}).get("count", 0):
        findings.append(["WARN", "Possible sensitive strings", report["sensitive_findings"]["count"], "Review line/field refs only."])
    if report.get("timestamp_backsteps"):
        findings.append(["WARN", "Timestamp backsteps", len(report["timestamp_backsteps"]), "Check append/backfill order."])
    if report.get("message_id_gaps"):
        findings.append(["WARN", "Message ID gaps", len(report["message_id_gaps"]), "Confirm gaps are expected."])
    if not findings:
        findings.append(["PASS", "No major findings", 0, "Ready for training-data review."])

    lines = [
        "# Training Data QA Report",
        "",
        f"Generated: {report.get('generated_at')}",
        f"Log path: `{report.get('log_path')}`",
        "",
        "## Executive Summary",
        "",
        f"Overall status: **{str(report.get('overall_status')).upper()}**",
        f"Overall score: **{score.get('overall_score')} / 100**",
        f"Lines analyzed: **{report.get('line_count')}**",
        f"Valid JSONL: **{report.get('valid_jsonl')}**",
        "",
        "## Scorecard",
        "",
        _markdown_table([[k, v] for k, v in score.items()], ["Category", "Score"]),
        "",
        "## Record Coverage",
        "",
        _markdown_table([[k, v] for k, v in sorted(report.get("record_type_counts", {}).items())], ["Record type", "Count"]),
        "",
        "## Findings",
        "",
        _markdown_table(findings, ["Severity", "Finding", "Count", "Recommended action"]),
        "",
        "## Sample References",
        "",
        "### Duplicate record_ids",
        "",
        _markdown_table([[s.get("record_id"), s.get("first_line"), s.get("duplicate_line")] for s in report.get("duplicate_record_ids", {}).get("samples", [])[:20]], ["record_id", "first line", "duplicate line"]) if report.get("duplicate_record_ids", {}).get("samples") else "None.",
        "",
        "### Sensitive findings (no raw values shown)",
        "",
        _markdown_table([[s.get("line"), s.get("field"), s.get("pattern")] for s in report.get("sensitive_findings", {}).get("samples", [])[:50]], ["Line", "Field", "Pattern"]) if report.get("sensitive_findings", {}).get("samples") else "None.",
        "",
        "### Logger error samples",
        "",
        _markdown_table([[s.get("line"), s.get("source"), s.get("path"), s.get("error_type")] for s in report.get("logger_errors", {}).get("samples", [])[:20]], ["Line", "Source", "Path", "Error type"]) if report.get("logger_errors", {}).get("samples") else "None.",
        "",
        "## Coverage Details",
        "",
        "```json",
        json.dumps(report.get("coverage", {}), indent=2, sort_keys=True),
        "```",
        "",
        "## Recommended Fixes",
        "",
    ]
    lines.extend([f"- {fix}" for fix in report.get("recommended_fixes", [])])
    lines.append("")
    return "\n".join(lines)


def write_reports(report: dict[str, Any], report_dir: Path | str = DEFAULT_REPORT_DIR) -> dict[str, str]:
    out_dir = Path(report_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    json_path = out_dir / f"training-qa-report-{stamp}.json"
    md_path = out_dir / f"training-qa-report-{stamp}.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    latest_json = out_dir / "training-qa-report-latest.json"
    latest_md = out_dir / "training-qa-report-latest.md"
    shutil.copyfile(json_path, latest_json)
    shutil.copyfile(md_path, latest_md)
    return {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
        "latest_json_path": str(latest_json),
        "latest_markdown_path": str(latest_md),
    }


def run_training_qa(log_path: Path | str = DEFAULT_LOG_PATH, report_dir: Path | str = DEFAULT_REPORT_DIR) -> dict[str, Any]:
    report = analyze_log(log_path)
    paths = write_reports(report, report_dir)
    return {"status": report["overall_status"], "scorecard": report["scorecard"], "paths": paths, "summary": {
        "line_count": report.get("line_count"),
        "valid_jsonl": report.get("valid_jsonl"),
        "record_type_counts": report.get("record_type_counts"),
        "finding_counts": {
            "duplicates": report.get("duplicate_record_ids", {}).get("count", 0),
            "logger_errors": report.get("logger_errors", {}).get("count", 0),
            "sensitive_findings": report.get("sensitive_findings", {}).get("count", 0),
            "timestamp_backsteps": len(report.get("timestamp_backsteps", [])),
            "message_id_gaps": len(report.get("message_id_gaps", [])),
        },
    }}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze ai-big-log for training-data QA and write Markdown/JSON reports.")
    parser.add_argument("--log-path", default=str(DEFAULT_LOG_PATH))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--json", action="store_true", help="Print machine-readable run summary")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_training_qa(args.log_path, args.report_dir)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Training QA status: {result['status'].upper()}")
        print(f"Overall score: {result['scorecard']['overall_score']} / 100")
        print(f"Markdown report: {result['paths']['markdown_path']}")
        print(f"JSON report: {result['paths']['json_path']}")
    return 0 if result["status"] in {"pass", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
