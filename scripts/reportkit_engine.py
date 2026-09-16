"""Dependency-free ReportKit validation and built-in report-site generation."""

from __future__ import annotations

import json
import hashlib
import os
import re
import shutil
import stat
from collections import Counter, deque
from datetime import datetime, timezone
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from json_schema import validate_instance

REPORTKIT_VERSION = "0.1.0"
SCHEMA_VERSION = "1.0"
MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_JSON_DEPTH = 64
MAX_JSON_NODES = 200000
SCHEMA_ROOT = Path(__file__).resolve().parents[1] / "schema"
VALID_STATUSES = {
    "healthy", "warning", "critical", "unknown", "not-applicable", "blocked",
    "in-progress", "pending-review", "not-started", "complete", "failed", "passed",
}
VALID_PRIORITIES = {"critical", "high", "medium", "low", "unknown"}
SENSITIVE_KEY = re.compile(
    r"(access[-_]?token|refresh[-_]?token|password|passwd|secret|credential|"
    r"connection[-_]?string|private[-_]?key)",
    re.IGNORECASE,
)
SENSITIVE_VALUE_PATTERNS = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.IGNORECASE)),
    ("authorization-header", re.compile(r"\bAuthorization\s*:\s*(?:Bearer|Basic)\s+\S+", re.IGNORECASE)),
    ("jwt-token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{8,}\b")),
    ("connection-string", re.compile(
        r"\b(?:AccountKey|SharedAccessSignature|Password|Pwd|ClientSecret)\s*=\s*[^;\s]+",
        re.IGNORECASE,
    )),
    ("signed-url", re.compile(r"https?://[^\s\"']+[?&](?:sig|signature|token|key|code)=[^&\s\"']+", re.IGNORECASE)),
)
PUBLIC_IDENTIFIER_PATTERNS = (
    ("email-address", re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")),
    ("internal-host", re.compile(r"\b(?:dev\.azure\.com|microsoft\.com|windows\.net)\b", re.IGNORECASE)),
    ("local-user-path", re.compile(r"\b[A-Za-z]:[\\/]Users[\\/][^\\/]+", re.IGNORECASE)),
)
SAFE_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
REQUIRED_CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; "
    "font-src 'self'; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"
)
OUTPUT_MARKER = ".reportkit-output.json"
BUILTIN_TEMPLATE_IDS = (
    "executive-health", "action-risk", "portfolio-team", "operational-health", "compliance-readiness",
)


def normalize_text_bytes(content: bytes) -> bytes:
    return content.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def load_json_bytes(content: bytes, source: str = "JSON document") -> dict[str, Any]:
    if len(content) > MAX_JSON_BYTES:
        raise ValueError(f"{source} exceeds the {MAX_JSON_BYTES}-byte limit")
    try:
        text = content.decode("utf-8")
        value = json.loads(
            text,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(f"non-finite number '{token}'")),
        )
    except UnicodeDecodeError as exception:
        raise ValueError(f"{source} must be UTF-8") from exception
    except RecursionError as exception:
        raise ValueError(f"{source} exceeds the supported nesting depth") from exception
    if not isinstance(value, dict):
        raise ValueError(f"{source} must contain a JSON object")
    pending = [(value, 0)]
    nodes = 0
    while pending:
        current, depth = pending.pop()
        nodes += 1
        if nodes > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
            raise ValueError(f"{source} exceeds the supported size or nesting budget")
        if isinstance(current, dict):
            pending.extend((child, depth + 1) for child in current.values())
        elif isinstance(current, list):
            pending.extend((child, depth + 1) for child in current)
    return value


def load_json(path: Path) -> dict[str, Any]:
    return load_json_bytes(path.read_bytes(), str(path))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def message(code: str, text: str, path: str = "") -> dict[str, str]:
    result = {"code": code, "message": text}
    if path:
        result["path"] = path
    return result


def validation_report(
    errors: list[dict[str, str]] | None = None,
    warnings: list[dict[str, str]] | None = None,
    info: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    errors = sorted(errors or [], key=lambda item: (item.get("path", ""), item["code"], item["message"]))
    warnings = sorted(warnings or [], key=lambda item: (item.get("path", ""), item["code"], item["message"]))
    info = sorted(info or [], key=lambda item: (item.get("path", ""), item["code"], item["message"]))
    status = "failed" if errors else ("passed-with-warnings" if warnings else "passed")
    return {
        "reportVersion": "1.0",
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "info": info,
        "summary": {
            "errorCount": len(errors),
            "warningCount": len(warnings),
            "infoCount": len(info),
        },
    }


def _is_datetime(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return "T" in value
    except ValueError:
        return False


def _is_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _walk_sensitive(
    value: Any,
    path: str,
    errors: list[dict[str, str]],
    public_sample: bool,
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if SENSITIVE_KEY.search(key):
                errors.append(message(
                    "sensitive-field",
                    f"Prohibited sensitive field '{key}' is present.",
                    child_path,
                ))
            _walk_sensitive(child, child_path, errors, public_sample)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_sensitive(child, f"{path}[{index}]", errors, public_sample)
    elif isinstance(value, str):
        for code, pattern in SENSITIVE_VALUE_PATTERNS:
            if pattern.search(value):
                errors.append(message(
                    "sensitive-value",
                    f"Value matches prohibited sensitive pattern '{code}'.",
                    path,
                ))
        if public_sample:
            for code, pattern in PUBLIC_IDENTIFIER_PATTERNS:
                if pattern.search(value):
                    errors.append(message(
                        "public-sample-identifier",
                        f"Public sample value matches prohibited identifier pattern '{code}'.",
                        path,
                    ))


def _require_string(
    parent: dict[str, Any],
    key: str,
    path: str,
    errors: list[dict[str, str]],
) -> None:
    if not isinstance(parent.get(key), str) or not parent[key].strip():
        errors.append(message("schema-required-string", f"'{key}' must be a non-empty string.", f"{path}.{key}"))


def validate_model_schema(model: dict[str, Any]) -> dict[str, Any]:
    """Validate the structural contract represented by reportkit-v1.schema.json."""
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    info: list[dict[str, str]] = []
    schema = load_json(SCHEMA_ROOT / "reportkit-v1.schema.json")
    errors.extend(validate_instance(model, schema))

    allowed_root = {
        "schemaVersion", "report", "metrics", "groups", "items",
        "trends", "highlights", "links", "provenance",
    }
    for key in sorted(set(model) - allowed_root):
        errors.append(message("schema-additional-property", f"Unexpected root property '{key}'.", key))

    if model.get("schemaVersion") != SCHEMA_VERSION:
        errors.append(message("schema-version", "schemaVersion must be '1.0'.", "schemaVersion"))

    report = model.get("report")
    if not isinstance(report, dict):
        errors.append(message("schema-required-object", "'report' must be an object.", "report"))
        report = {}
    for key in ("id", "title", "generatedAt", "dataAsOf", "classification"):
        _require_string(report, key, "report", errors)
    for key in ("generatedAt", "dataAsOf"):
        if key in report and not _is_datetime(report[key]):
            errors.append(message("schema-date-time", f"report.{key} must be an ISO-8601 date-time.", f"report.{key}"))
    if "status" in report and report["status"] not in VALID_STATUSES:
        errors.append(message("schema-status", f"Unknown report status '{report['status']}'.", "report.status"))
    period = report.get("period")
    if period is not None:
        if not isinstance(period, dict):
            errors.append(message("schema-period", "report.period must be an object.", "report.period"))
        else:
            _require_string(period, "label", "report.period", errors)
            for key in ("startDate", "endDate"):
                if key in period and not _is_date(period[key]):
                    errors.append(message("schema-date", f"report.period.{key} must be YYYY-MM-DD.", f"report.period.{key}"))

    collections = ("metrics", "groups", "items", "trends", "highlights", "links")
    for key in collections:
        if key in model and not isinstance(model[key], list):
            errors.append(message("schema-array", f"'{key}' must be an array.", key))

    for index, metric in enumerate(model.get("metrics", [])):
        path = f"metrics[{index}]"
        if not isinstance(metric, dict):
            errors.append(message("schema-object", "Metric must be an object.", path))
            continue
        for key in ("id", "label", "unit"):
            _require_string(metric, key, path, errors)
        if (
            "value" not in metric
            or isinstance(metric["value"], bool)
            or not isinstance(metric["value"], (int, float, str))
        ):
            errors.append(message("schema-metric-value", "Metric value must be a number or string.", f"{path}.value"))
        if "status" in metric and metric["status"] not in VALID_STATUSES:
            errors.append(message("schema-status", f"Unknown metric status '{metric['status']}'.", f"{path}.status"))

    for index, group in enumerate(model.get("groups", [])):
        path = f"groups[{index}]"
        if not isinstance(group, dict):
            errors.append(message("schema-object", "Group must be an object.", path))
            continue
        _require_string(group, "id", path, errors)
        _require_string(group, "label", path, errors)
        if "status" in group and group["status"] not in VALID_STATUSES:
            errors.append(message("schema-status", f"Unknown group status '{group['status']}'.", f"{path}.status"))

    for index, item in enumerate(model.get("items", [])):
        path = f"items[{index}]"
        if not isinstance(item, dict):
            errors.append(message("schema-object", "Item must be an object.", path))
            continue
        for key in ("id", "title", "status"):
            _require_string(item, key, path, errors)
        if item.get("status") not in VALID_STATUSES:
            errors.append(message("schema-status", f"Unknown item status '{item.get('status')}'.", f"{path}.status"))
        if "priority" in item and item["priority"] not in VALID_PRIORITIES:
            errors.append(message("schema-priority", f"Unknown item priority '{item['priority']}'.", f"{path}.priority"))
        for key in ("dueDate", "eta", "nextActionDate"):
            if item.get(key) is not None and not _is_date(item[key]):
                errors.append(message("schema-date", f"{path}.{key} must be YYYY-MM-DD or null.", f"{path}.{key}"))

    provenance = model.get("provenance")
    if not isinstance(provenance, dict):
        errors.append(message("schema-required-object", "'provenance' must be an object.", "provenance"))
    else:
        adapter = provenance.get("adapter")
        if not isinstance(adapter, dict):
            errors.append(message("schema-required-object", "provenance.adapter must be an object.", "provenance.adapter"))
        else:
            _require_string(adapter, "id", "provenance.adapter", errors)
            _require_string(adapter, "version", "provenance.adapter", errors)
        if not isinstance(provenance.get("sources"), list) or not provenance.get("sources"):
            errors.append(message("schema-sources", "provenance.sources must be a non-empty array.", "provenance.sources"))
        if not isinstance(provenance.get("recordCounts"), dict) or not provenance.get("recordCounts"):
            errors.append(message("schema-record-counts", "provenance.recordCounts must be a non-empty object.", "provenance.recordCounts"))

    public_sample = str(report.get("classification", "")).strip().lower() == "public sample"
    _walk_sensitive(model, "", errors, public_sample)
    return validation_report(errors, warnings, info)


def validate_config(config: dict[str, Any], capability: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    schema = load_json(SCHEMA_ROOT / "configuration-v1.schema.json")
    errors.extend(validate_instance(config, schema))
    allowed_root = {
        "version", "template", "theme", "freshnessThresholdsMinutes", "output",
    }
    for key in sorted(set(config) - allowed_root):
        errors.append(message("config-additional-property", f"Unexpected configuration property '{key}'.", key))
    if config.get("version") != "1.0":
        errors.append(message("config-version", "Configuration version must be '1.0'.", "version"))

    template = config.get("template")
    if not isinstance(template, dict):
        errors.append(message("config-template", "template must be an object.", "template"))
    else:
        for key in sorted(set(template) - {"id", "version"}):
            errors.append(message("config-additional-property", f"Unexpected template property '{key}'.", f"template.{key}"))
        if template.get("id") != capability.get("id"):
            errors.append(message("config-template-id", "Configured template ID does not match the capability.", "template.id"))
        if template.get("version") != capability.get("version"):
            errors.append(message("config-template-version", "Configured template version does not match the capability.", "template.version"))

    theme = config.get("theme", {})
    if not isinstance(theme, dict):
        errors.append(message("config-theme", "theme must be an object.", "theme"))
    else:
        for key in sorted(set(theme) - {"name", "primaryColor"}):
            errors.append(message("config-additional-property", f"Unexpected theme property '{key}'.", f"theme.{key}"))
        if "name" in theme and (not isinstance(theme["name"], str) or not theme["name"].strip()):
            errors.append(message("config-theme-name", "theme.name must be a non-empty string.", "theme.name"))
        color = theme.get("primaryColor", "#2875e2")
        if not isinstance(color, str) or not SAFE_COLOR.fullmatch(color):
            errors.append(message(
                "config-color",
                "theme.primaryColor must be a six-digit hexadecimal color.",
                "theme.primaryColor",
            ))

    thresholds = config.get("freshnessThresholdsMinutes", {})
    if not isinstance(thresholds, dict):
        errors.append(message(
            "config-freshness-thresholds",
            "freshnessThresholdsMinutes must be an object.",
            "freshnessThresholdsMinutes",
        ))
    else:
        for key in sorted(set(thresholds) - {"fresh", "stale"}):
            errors.append(message("config-additional-property", f"Unexpected threshold property '{key}'.", f"freshnessThresholdsMinutes.{key}"))
        values: dict[str, int] = {}
        for key, default in (("fresh", 60), ("stale", 1440)):
            value = thresholds.get(key, default)
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 525_600:
                errors.append(message(
                    "config-freshness-threshold",
                    f"freshnessThresholdsMinutes.{key} must be an integer from 0 to 525600.",
                    f"freshnessThresholdsMinutes.{key}",
                ))
            else:
                values[key] = value
        if values.get("fresh", 0) > values.get("stale", 525_600):
            errors.append(message(
                "config-freshness-order",
                "The fresh threshold cannot exceed the stale threshold.",
                "freshnessThresholdsMinutes",
            ))

    output = config.get("output", {})
    if not isinstance(output, dict):
        errors.append(message("config-output", "output must be an object.", "output"))
    else:
        for key in sorted(set(output) - {"selfContained", "includePrototypeNotice"}):
            errors.append(message("config-additional-property", f"Unexpected output property '{key}'.", f"output.{key}"))
        for key in ("selfContained", "includePrototypeNotice"):
            if key in output and not isinstance(output[key], bool):
                errors.append(message("config-boolean", f"output.{key} must be a boolean.", f"output.{key}"))
        if output.get("selfContained") is False:
            errors.append(message(
                "config-self-contained",
                "The current renderer requires self-contained output.",
                "output.selfContained",
            ))
    return validation_report(errors)


def validate_model_semantics(model: dict[str, Any], capability: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    info: list[dict[str, str]] = []

    if model.get("schemaVersion") not in capability.get("supportedSchemaVersions", []):
        errors.append(message(
            "unsupported-schema",
            f"Template does not support schema version '{model.get('schemaVersion')}'.",
            "schemaVersion",
        ))

    for section in capability.get("requiredSections", []):
        if section not in model:
            errors.append(message("missing-section", f"Template requires section '{section}'.", section))
        elif isinstance(model[section], list) and not model[section]:
            errors.append(message("empty-required-section", f"Template requires non-empty section '{section}'.", section))

    for expression in capability.get("requiredFields", []):
        values: list[tuple[str, Any]] = [("", model)]
        valid_expression = True
        for segment in expression.split("."):
            is_collection = segment.endswith("[]")
            key = segment[:-2] if is_collection else segment
            next_values: list[tuple[str, Any]] = []
            for current_path, current in values:
                field_path = f"{current_path}.{key}".lstrip(".")
                if not isinstance(current, dict) or key not in current:
                    errors.append(message(
                        "missing-required-field",
                        f"Template requires field '{expression}'.",
                        field_path,
                    ))
                    valid_expression = False
                    continue
                child = current[key]
                if is_collection:
                    if not isinstance(child, list) or not child:
                        errors.append(message(
                            "missing-required-field",
                            f"Template requires a non-empty collection for '{expression}'.",
                            field_path,
                        ))
                        valid_expression = False
                    else:
                        next_values.extend((f"{field_path}[{index}]", item) for index, item in enumerate(child))
                else:
                    next_values.append((field_path, child))
            values = next_values
            if not valid_expression:
                break
        if valid_expression:
            for field_path, value in values:
                if value is None or (isinstance(value, str) and not value.strip()):
                    errors.append(message(
                        "missing-required-field",
                        f"Template requires a value for '{expression}'.",
                        field_path,
                    ))

    for collection in ("metrics", "groups", "items", "trends", "highlights"):
        ids: list[str] = [
            entry.get("id") for entry in model.get(collection, [])
            if isinstance(entry, dict) and isinstance(entry.get("id"), str)
        ]
        duplicates = sorted(identifier for identifier, count in Counter(ids).items() if count > 1)
        for identifier in duplicates:
            errors.append(message("duplicate-id", f"Duplicate {collection} ID '{identifier}'.", collection))

    group_ids = {group["id"] for group in model.get("groups", []) if isinstance(group, dict) and "id" in group}
    item_ids = {item["id"] for item in model.get("items", []) if isinstance(item, dict) and "id" in item}
    metric_ids = {metric["id"] for metric in model.get("metrics", []) if isinstance(metric, dict) and "id" in metric}

    for index, item in enumerate(model.get("items", [])):
        for group_id in item.get("groupIds", []):
            if group_id not in group_ids:
                errors.append(message("unresolved-group", f"Unknown group ID '{group_id}'.", f"items[{index}].groupIds"))
            else:
                group = next(group for group in model.get("groups", []) if group.get("id") == group_id)
                if "itemIds" in group and item["id"] not in group["itemIds"]:
                    errors.append(message(
                        "group-item-mismatch",
                        f"Item '{item['id']}' references group '{group_id}', but the group does not reference the item.",
                        f"items[{index}].groupIds",
                    ))
    for index, group in enumerate(model.get("groups", [])):
        for item_id in group.get("itemIds", []):
            if item_id not in item_ids:
                errors.append(message("unresolved-item", f"Unknown item ID '{item_id}'.", f"groups[{index}].itemIds"))
            else:
                item = next(item for item in model.get("items", []) if item.get("id") == item_id)
                if "groupIds" in item and group["id"] not in item["groupIds"]:
                    errors.append(message(
                        "group-item-mismatch",
                        f"Group '{group['id']}' references item '{item_id}', but the item does not reference the group.",
                        f"groups[{index}].itemIds",
                    ))
        for metric_id in group.get("metricIds", []):
            if metric_id not in metric_ids:
                errors.append(message("unresolved-metric", f"Unknown metric ID '{metric_id}'.", f"groups[{index}].metricIds"))
        for child_id in group.get("childGroupIds", []):
            if child_id not in group_ids:
                errors.append(message("unresolved-group", f"Unknown child group ID '{child_id}'.", f"groups[{index}].childGroupIds"))
    for index, highlight in enumerate(model.get("highlights", [])):
        for group_id in highlight.get("groupIds", []):
            if group_id not in group_ids:
                errors.append(message("unresolved-group", f"Unknown group ID '{group_id}'.", f"highlights[{index}].groupIds"))
        for item_id in highlight.get("itemIds", []):
            if item_id not in item_ids:
                errors.append(message("unresolved-item", f"Unknown item ID '{item_id}'.", f"highlights[{index}].itemIds"))

    children = {group["id"]: group.get("childGroupIds", []) for group in model.get("groups", [])}
    indegree = dict.fromkeys(children, 0)
    for references in children.values():
        for child in references:
            if child in indegree:
                indegree[child] += 1
    ready = deque(sorted(identifier for identifier, count in indegree.items() if count == 0))
    visited = 0
    while ready:
        identifier = ready.popleft()
        visited += 1
        for child in children[identifier]:
            if child in indegree:
                indegree[child] -= 1
                if indegree[child] == 0:
                    ready.append(child)
    if visited != len(children):
        errors.append(message("group-cycle", "Child group references must not contain cycles.", "groups"))

    report = model.get("report", {})
    generated = datetime.fromisoformat(report["generatedAt"].replace("Z", "+00:00"))
    data_as_of = datetime.fromisoformat(report["dataAsOf"].replace("Z", "+00:00"))
    if data_as_of > generated:
        errors.append(message("future-data", "dataAsOf cannot be later than generatedAt.", "report.dataAsOf"))

    provenance = model.get("provenance", {})
    record_counts = provenance.get("recordCounts", {})
    canonical_count = record_counts.get("canonicalItems")
    if canonical_count is not None and canonical_count != len(model.get("items", [])):
        errors.append(message(
            "canonical-count-mismatch",
            f"provenance.recordCounts.canonicalItems is {canonical_count}, but items contains {len(model.get('items', []))} records.",
            "provenance.recordCounts.canonicalItems",
        ))
    raw_count = record_counts.get("raw")
    declared_source_total = record_counts.get("sourceTotal")
    source_counts = [
        source.get("recordCount") for source in provenance.get("sources", [])
        if isinstance(source, dict)
    ]
    if declared_source_total is not None and source_counts and all(isinstance(count, int) for count in source_counts):
        source_total = sum(source_counts)
        if declared_source_total != source_total:
            errors.append(message(
                "source-count-mismatch",
                f"provenance.recordCounts.sourceTotal is {declared_source_total}, but source recordCount values total {source_total}.",
                "provenance.recordCounts.sourceTotal",
            ))
        if raw_count is not None and raw_count != declared_source_total:
            errors.append(message(
                "source-count-mismatch",
                f"provenance.recordCounts.raw is {raw_count}, but sourceTotal is {declared_source_total}.",
                "provenance.recordCounts.raw",
            ))

    if not model.get("trends"):
        warnings.append(message("missing-trends", "No trend history is available.", "trends"))
    if not model.get("highlights"):
        info.append(message("missing-highlights", "No highlights were supplied.", "highlights"))

    return validation_report(errors, warnings, info)


def merge_reports(*reports: dict[str, Any]) -> dict[str, Any]:
    def unique(kind: str) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for report in reports:
            for entry in report[kind]:
                key = (entry.get("path", ""), entry["code"], entry["message"])
                if key not in seen:
                    seen.add(key)
                    result.append(entry)
        return result

    return validation_report(
        unique("errors"),
        unique("warnings"),
        unique("info"),
    )


def validate_model(model: dict[str, Any], capability: dict[str, Any]) -> dict[str, Any]:
    schema_report = validate_model_schema(model)
    if schema_report["errors"]:
        return schema_report
    return merge_reports(schema_report, validate_model_semantics(model, capability))


def _format_datetime(value: str) -> str:
    instant = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    return f"{instant.day:02d} {months[instant.month - 1]} {instant.year:04d}, {instant.hour:02d}:{instant.minute:02d} UTC"


def _freshness(model: dict[str, Any], config: dict[str, Any]) -> tuple[str, str]:
    report = model["report"]
    generated = datetime.fromisoformat(report["generatedAt"].replace("Z", "+00:00"))
    data_as_of = datetime.fromisoformat(report["dataAsOf"].replace("Z", "+00:00"))
    minutes = max(0, int((generated - data_as_of).total_seconds() // 60))
    thresholds = config.get("freshnessThresholdsMinutes", {})
    fresh_limit = int(thresholds.get("fresh", 60))
    stale_limit = int(thresholds.get("stale", 1440))
    if minutes <= fresh_limit:
        return "fresh", f"Fresh · {minutes} min old"
    if minutes <= stale_limit:
        return "warning", f"Aging · {minutes} min old"
    return "critical", f"Stale · {minutes} min old"


def _owner_label(owner: Any) -> str:
    if not isinstance(owner, dict):
        return "Unassigned"
    return str(owner.get("team") or owner.get("displayName") or owner.get("alias") or "Unassigned")


def _metric_sort(metric: dict[str, Any]) -> tuple[int, str]:
    return (int(metric.get("order", 9999)), str(metric.get("id", "")))


def _priority_sort(item: dict[str, Any]) -> tuple[int, str, str]:
    rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}
    return (rank.get(item.get("priority", "unknown"), 4), str(item.get("dueDate") or "9999-12-31"), item["id"])


def render_executive_health(model: dict[str, Any], config: dict[str, Any]) -> str:
    report = model["report"]
    metrics = sorted(model.get("metrics", []), key=_metric_sort)[:4]
    highlights = sorted(model.get("highlights", []), key=lambda item: (item.get("order", 9999), item["id"]))[:4]
    critical_items = sorted(
        [item for item in model.get("items", []) if item.get("priority") in {"critical", "high"}],
        key=_priority_sort,
    )[:5]
    group_labels = {group["id"]: group["label"] for group in model.get("groups", [])}
    concentration: Counter[str] = Counter()
    for item in model.get("items", []):
        if item.get("status") in {"warning", "critical", "blocked", "failed"}:
            for group_id in item.get("groupIds", []):
                concentration[group_labels.get(group_id, group_id)] += 1
    concentration_rows = sorted(concentration.items(), key=lambda pair: (-pair[1], pair[0]))[:6]
    max_concentration = max((count for _, count in concentration_rows), default=1)
    freshness_class, freshness_label = _freshness(model, config)

    metric_html = "\n".join(
        f"""<article class="metric metric-{escape(metric.get('status', 'unknown'))}">
          <p class="metric-label">{escape(metric['label'])}</p>
          <p class="metric-value">{escape(str(metric['value']))}</p>
          <p class="metric-unit">{escape(metric['unit'])}</p>
          <p class="metric-context">{escape(metric.get('description', ''))}</p>
        </article>"""
        for metric in metrics
    ) or '<div class="empty-state">No metrics supplied.</div>'

    highlight_html = "\n".join(
        f"""<li><span class="signal signal-{escape(item.get('status', 'unknown'))}">{escape(item['type'])}</span>
        <div><strong>{escape(item['title'])}</strong><p>{escape(item.get('summary', ''))}</p></div></li>"""
        for item in highlights
    ) or '<li class="empty-state">No confirmed changes were supplied.</li>'

    decision_rows = "\n".join(
        f"""<tr>
          <td><strong>{escape(item['title'])}</strong><span>{escape(item.get('summary', ''))}</span></td>
          <td><span class="badge badge-{escape(item.get('priority', 'unknown'))}">{escape(item.get('priority', 'unknown'))}</span></td>
          <td>{escape(_owner_label(item.get('accountableOwner')))}</td>
          <td>{escape(str(item.get('dueDate') or 'Not set'))}</td>
          <td>{escape(item.get('nextAction') or item.get('statusText') or 'Review required')}</td>
        </tr>"""
        for item in critical_items
    ) or '<tr><td colspan="5" class="empty-state">No leadership decisions require attention.</td></tr>'

    concentration_html = "\n".join(
        f"""<li><div><span>{escape(label)}</span><strong>{count} records</strong></div>
        <div class="bar"><span style="width:{(count / max_concentration) * 100:.1f}%"></span></div></li>"""
        for label, count in concentration_rows
    ) or '<li class="empty-state">No risk concentration is present.</li>'

    trend = next(iter(sorted(model.get("trends", []), key=lambda item: (item.get("order", 9999), item["id"]))), None)
    trend_html = '<div class="empty-state">No trend history is available.</div>'
    trend_description = "No dated observations supplied"
    if trend:
        observations = trend["observations"]
        maximum = max((abs(observation["value"]) for observation in observations), default=0) or 1
        trend_description = f"{trend['label']} ({trend['unit']})"
        trend_html = '<div class="trend" role="img" aria-label="' + escape(trend["label"]) + '">' + "".join(
            f'<div><span class="trend-bar" title="{escape(str(observation["value"]))} {escape(trend["unit"])}" style="height:{abs(observation["value"]) / maximum * 100:.1f}%"></span>'
            f'<small>{escape(observation["date"][5:])}</small><strong>{escape(str(observation["value"]))}</strong></div>'
            for observation in observations
        ) + "</div>"

    period = report.get("period", {}).get("label", "")
    classification = report["classification"]
    status = report.get("status", "unknown")
    primary = config.get("theme", {}).get("primaryColor", "#2875e2")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'">
  <meta name="description" content="{escape(report.get('subtitle', report['title']))}">
  <title>{escape(report['title'])} | ReportKit</title>
  <style>
    :root{{--navy:#07192e;--ink:#14213a;--muted:#59687d;--canvas:#edf2f7;--surface:#fff;--line:#d7e0eb;--primary:{primary};--green:#16855f;--amber:#b65f00;--red:#c83e4d}}
    *{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--canvas);color:var(--ink);font:16px/1.5 "Segoe UI",Arial,sans-serif}}a{{color:inherit}}a:focus-visible{{outline:3px solid #66d0ff;outline-offset:3px}}.skip{{position:fixed;left:12px;top:12px;transform:translateY(-160%);background:#fff;padding:10px;z-index:10}}.skip:focus{{transform:none}}.shell{{width:min(calc(100% - 36px),1320px);margin:auto}}header{{color:#fff;background:linear-gradient(140deg,var(--navy),#103154)}}.mast{{min-height:76px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #ffffff25}}.brand{{font-weight:800}}.classification{{border:1px solid #ffffff55;border-radius:99px;padding:6px 10px;font-size:.75rem;text-transform:uppercase}}.hero{{display:grid;grid-template-columns:1.2fr .8fr;gap:42px;padding:42px 0 56px;align-items:end}}.eyebrow{{color:#66d0ff;font-size:.78rem;font-weight:800;text-transform:uppercase;letter-spacing:.12em}}h1{{font-size:clamp(2.4rem,5vw,4.6rem);line-height:1;margin:8px 0}}.subtitle{{color:#bfd0e1}}.status-card{{padding:22px;border:1px solid #ffffff30;border-radius:16px;background:#ffffff12}}.status-card h2{{margin:6px 0}}.meta{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:16px;font-size:.76rem;color:#c7d5e3}}.freshness{{font-weight:800}}.freshness.fresh{{color:#8fe0bd}}.freshness.warning{{color:#ffd27b}}.freshness.critical{{color:#ff9eaa}}main{{padding-bottom:42px}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:-22px}}.metric,.card{{background:#fff;border:1px solid var(--line);border-radius:17px;box-shadow:0 14px 38px #14284812}}.metric{{padding:21px;border-top:4px solid var(--primary)}}.metric-warning{{border-top-color:var(--amber)}}.metric-critical{{border-top-color:var(--red)}}.metric-healthy{{border-top-color:var(--green)}}.metric-label{{font-size:.8rem;font-weight:750;color:var(--muted)}}.metric-value{{font-size:2.4rem;font-weight:800;margin:10px 0 0}}.metric-unit,.metric-context{{font-size:.76rem;color:var(--muted)}}.grid{{display:grid;grid-template-columns:1.5fr .8fr;gap:16px;margin-top:16px}}.grid>*{{min-width:0}}.card{{padding:24px}}.card h2{{margin:0 0 4px}}.section-copy{{margin:0 0 18px;color:var(--muted);font-size:.84rem}}.signals{{list-style:none;padding:0;margin:0}}.signals li{{display:grid;grid-template-columns:auto 1fr;gap:12px;padding:13px 0;border-top:1px solid var(--line)}}.signals p{{margin:3px 0;color:var(--muted);font-size:.78rem}}.signal,.badge{{display:inline-flex;align-self:start;border-radius:99px;padding:4px 8px;background:#edf1f5;font-size:.68rem;font-weight:800;text-transform:uppercase}}.signal-healthy,.badge-low{{background:#e6f6ef;color:#126848}}.signal-warning,.badge-high{{background:#fff2d8;color:#8e4c00}}.signal-critical,.badge-critical{{background:#ffeaed;color:#a42d3d}}.trend{{height:220px;display:flex;align-items:end;gap:10px;border-bottom:1px solid var(--line);padding:12px}}.trend>div{{height:100%;flex:1;display:flex;flex-direction:column;justify-content:end;align-items:center;gap:4px}}.trend-bar{{display:block;width:70%;background:linear-gradient(var(--primary),#76aaf0);border-radius:6px 6px 0 0}}.trend small{{color:var(--muted)}}table{{width:100%;border-collapse:collapse;table-layout:fixed}}th,td{{padding:13px;text-align:left;border-top:1px solid var(--line);vertical-align:top;overflow-wrap:anywhere}}th{{font-size:.7rem;text-transform:uppercase;color:var(--muted);background:#f7f9fb}}td strong,td span{{display:block}}td span{{color:var(--muted);font-size:.75rem;margin-top:3px}}.attention{{margin-top:16px;overflow:hidden;padding:0}}.attention h2,.attention .section-copy{{margin-left:24px;margin-right:24px}}.attention h2{{margin-top:22px}}.concentration{{list-style:none;padding:0;margin:0}}.concentration li{{margin:13px 0}}.concentration li>div:first-child{{display:flex;justify-content:space-between;font-size:.8rem}}.bar{{height:9px;background:#e9edf2;border-radius:99px;overflow:hidden;margin-top:6px}}.bar span{{display:block;height:100%;background:var(--primary)}}.empty-state{{padding:18px;color:var(--muted);background:#f7f9fb;border-radius:10px}}footer{{display:flex;justify-content:space-between;gap:20px;margin-top:18px;padding:20px 0;color:var(--muted);font-size:.76rem}}
    @media(max-width:900px){{.hero,.grid{{grid-template-columns:1fr}}.metrics{{grid-template-columns:repeat(2,1fr)}}}}
    @media(max-width:620px){{.metrics{{grid-template-columns:1fr}}table,tbody,tr,td{{display:block;width:100%}}thead{{display:none}}tr{{border-top:1px solid var(--line);padding:10px}}td{{border:0;padding:7px}}footer{{display:grid}}}}
    @media print{{body{{background:#fff}}header{{background:#fff;color:#111;border-bottom:2px solid #111}}.subtitle,.meta{{color:#444}}.metric,.card{{box-shadow:none;break-inside:avoid}}.attention{{break-before:page}}}}
  </style>
</head>
<body data-template="executive-health" data-template-version="1.0" data-item-count="{len(model.get('items', []))}">
  <a class="skip" href="#main">Skip to report</a>
  <header>
    <div class="shell mast"><span class="brand">ReportKit · Executive Health v1.0</span><span class="classification">{escape(classification)}</span></div>
    <div class="shell hero">
      <div><p class="eyebrow">Leadership health brief</p><h1>{escape(report['title'])}</h1><p class="subtitle">{escape(report.get('subtitle', ''))} · {escape(period)}</p></div>
      <section class="status-card" aria-label="Overall status {escape(status)}">
        <p class="eyebrow">Overall status</p><h2>{escape(report.get('statusLabel', status.replace('-', ' ').title()))}</h2>
        <p>{escape(report.get('statusSummary', ''))}</p>
        <div class="meta"><span>Data as of<br><strong>{escape(_format_datetime(report['dataAsOf']))}</strong></span><span>Generated<br><strong>{escape(_format_datetime(report['generatedAt']))}</strong></span><span class="freshness {freshness_class}">{escape(freshness_label)}</span><span>Classification<br><strong>{escape(classification)}</strong></span></div>
      </section>
    </div>
  </header>
  <main id="main" class="shell">
    <section class="metrics" aria-label="Key metrics">{metric_html}</section>
    <div class="grid">
      <section id="trend" class="card"><h2>Health trend</h2><p class="section-copy">{escape(trend_description)}</p>{trend_html}</section>
      <aside id="signals" class="card"><h2>Confirmed signals</h2><p class="section-copy">Changes supplied by the source adapter</p><ul class="signals">{highlight_html}</ul></aside>
    </div>
    <section id="attention" class="card attention"><h2>Leadership attention</h2><p class="section-copy">Highest-priority records ordered by priority, due date, and stable ID</p><table><caption class="skip">Leadership decisions requiring attention</caption><thead><tr><th>Decision or risk</th><th>Priority</th><th>Accountable owner</th><th>Due</th><th>Next action</th></tr></thead><tbody>{decision_rows}</tbody></table></section>
    <div class="grid">
      <section class="card"><h2>Risk concentration</h2><p class="section-copy">Attention records by group</p><ul class="concentration">{concentration_html}</ul></section>
      <aside class="card"><h2>Report identity</h2><p><strong>{escape(report['id'])}</strong></p><p class="section-copy">Schema {SCHEMA_VERSION} · ReportKit {REPORTKIT_VERSION}<br>Adapter {escape(model['provenance']['adapter']['id'])}@{escape(model['provenance']['adapter']['version'])}<br>{len(model.get('items', []))} canonical records</p></aside>
    </div>
    <footer><span>Data as of {escape(_format_datetime(report['dataAsOf']))} · Generated {escape(_format_datetime(report['generatedAt']))}</span><span class="freshness {freshness_class}">{escape(freshness_label)}</span></footer>
  </main>
</body>
</html>
"""


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.duplicate_ids: set[str] = set()
        self.references: list[tuple[str, str, str]] = []
        self.unsafe_elements: list[str] = []
        self.event_handlers: list[str] = []
        self.has_main = False
        self.h1_count = 0
        self.has_classification = False
        self.has_freshness = False
        self.csp_values: list[str] = []
        self.item_counts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if attributes.get("id"):
            identifier = str(attributes["id"])
            if identifier in self.ids:
                self.duplicate_ids.add(identifier)
            self.ids.add(identifier)
        for attribute in ("href", "src", "action"):
            if attributes.get(attribute):
                self.references.append((tag, attribute, str(attributes[attribute])))
        if tag in {"script", "iframe", "object", "embed", "form", "base"}:
            self.unsafe_elements.append(tag)
        for name in attributes:
            if name.lower().startswith("on"):
                self.event_handlers.append(name)
        if tag == "meta":
            http_equiv = str(attributes.get("http-equiv", "")).lower()
            if http_equiv == "content-security-policy":
                self.csp_values.append(str(attributes.get("content", "")))
            if http_equiv == "refresh":
                self.unsafe_elements.append("meta-refresh")
        if tag == "body" and attributes.get("data-item-count") is not None:
            self.item_counts.append(str(attributes["data-item-count"]))
        self.has_main |= tag == "main"
        self.h1_count += int(tag == "h1")
        classes = str(attributes.get("class", "")).split()
        self.has_classification |= "classification" in classes
        self.has_freshness |= "freshness" in classes


def _decode_reference_path(value: str) -> str:
    decoded = value
    for _ in range(3):
        next_value = unquote(decoded)
        if next_value == decoded:
            break
        decoded = next_value
    return decoded.replace("\\", "/")


def _safe_relative_path(root: Path, base: Path, value: str) -> Path | None:
    if not value or any(ord(character) < 32 for character in value):
        return None
    decoded = _decode_reference_path(value)
    if any(ord(character) < 32 for character in decoded):
        return None
    if (
        decoded.startswith(("/", "//"))
        or re.match(r"^[A-Za-z]:", decoded)
        or decoded.startswith("\\\\")
    ):
        return None
    parts = [part for part in decoded.split("/") if part not in {"", "."}]
    if not parts or ".." in parts or ":" in parts[0]:
        return None
    for part in parts:
        stem = part.rstrip(" .").split(".", 1)[0].upper()
        if not part.rstrip(" .") or stem in WINDOWS_RESERVED_NAMES:
            return None
    candidate = (base / Path(*parts)).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def _load_json_for_validation(path: Path, errors: list[dict[str, str]]) -> dict[str, Any] | None:
    try:
        return load_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exception:
        errors.append(message("invalid-json", f"Invalid JSON document: {exception}", path.name))
        return None


def lexical_absolute_path(path: Path) -> Path:
    """Return an absolute normalized path without resolving links or reparse points."""
    return Path(os.path.abspath(os.fspath(path)))


def _path_lexists(path: Path) -> bool:
    return os.path.lexists(os.fspath(path))


def _is_reparse_point(path: Path) -> bool:
    try:
        status = os.lstat(path)
    except OSError:
        return False
    attributes = getattr(status, "st_file_attributes", 0)
    return stat.S_ISLNK(status.st_mode) or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _first_reparse_component(path: Path) -> Path | None:
    absolute = lexical_absolute_path(path)
    components = [*reversed(absolute.parents), absolute]
    for component in components:
        if _path_lexists(component) and _is_reparse_point(component):
            return component
    return None


def validate_site(site: Path, expected_item_count: int | None = None) -> dict[str, Any]:
    from artifact_identity import verify_identity
    from site_inventory import inspect_site_inventory, relative_site_path

    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    info: list[dict[str, str]] = []
    site = lexical_absolute_path(site)
    redirected = _first_reparse_component(site)
    if redirected is not None:
        errors.append(message("site-path-redirection", "Site path cannot contain a symbolic link, junction, or reparse point.", str(redirected)))
        return validation_report(errors, warnings, info)
    inventory_files, inventory_errors = inspect_site_inventory(site)
    errors.extend(inventory_errors)
    if inventory_errors:
        return validation_report(errors, warnings, info)
    index = site / "index.html"
    manifest_path = site / "report-manifest.json"
    validation_path = site / "validation-report.json"
    if not index.is_file():
        errors.append(message("missing-index", "Generated site is missing index.html.", "index.html"))
        return validation_report(errors, warnings, info)
    if not manifest_path.is_file():
        errors.append(message("missing-manifest", "Generated site is missing report-manifest.json.", "report-manifest.json"))
    if not validation_path.is_file():
        errors.append(message("missing-validation-report", "Generated site is missing validation-report.json.", "validation-report.json"))

    html_files = sorted(
        path for path in inventory_files if path.suffix.lower() in {".html", ".htm"}
    )
    parsed_pages: dict[str, tuple[Path, SiteParser]] = {}
    for page in html_files:
        relative = relative_site_path(site, page)
        if page.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(page)):
            errors.append(message("site-link-redirection", "Site files cannot be symbolic links or junctions.", relative))
            continue
        try:
            html_text = page.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(message("invalid-html-encoding", "HTML must be UTF-8.", relative))
            continue
        parser = SiteParser()
        parser.feed(html_text)
        parsed_pages[relative] = (page, parser)
        for element in sorted(set(parser.unsafe_elements)):
            errors.append(message("active-content", f"Element '{element}' is not allowed.", relative))
        for handler in sorted(set(parser.event_handlers)):
            errors.append(message("event-handler", f"Inline event handler '{handler}' is not allowed.", relative))
        for identifier in sorted(parser.duplicate_ids):
            errors.append(message("duplicate-html-id", f"Duplicate HTML ID '{identifier}'.", relative))
        if not parser.has_main or parser.h1_count != 1:
            errors.append(message("accessibility-structure", "Every page must contain main and exactly one h1.", relative))
        if not parser.has_classification:
            errors.append(message("missing-classification", "Classification is not visibly rendered.", relative))
        if not parser.has_freshness:
            errors.append(message("missing-freshness", "Freshness is not visibly rendered.", relative))
        if REQUIRED_CSP not in parser.csp_values:
            errors.append(message("invalid-csp", "Generated HTML must declare the exact ReportKit content security policy.", relative))

    for relative, (page, parser) in parsed_pages.items():
        for tag, attribute, reference in parser.references:
            parsed = urlsplit(reference)
            if parsed.scheme or parsed.netloc or reference.startswith("//"):
                errors.append(message(
                    "unsafe-url",
                    f"External or active URL '{reference}' is not allowed in self-contained output.",
                    relative,
                ))
                continue
            if parsed.path:
                target = _safe_relative_path(site, page.parent, parsed.path)
                if target is None:
                    errors.append(message("unsafe-path", f"Reference '{reference}' escapes or violates the site path policy.", relative))
                    continue
            else:
                target = page
            if not target.is_file():
                errors.append(message("broken-link", f"Reference '{reference}' does not resolve.", relative))
                continue
            if parsed.fragment and target.suffix.lower() in {".html", ".htm"}:
                target_entry = parsed_pages.get(relative_site_path(site, target))
                target_parser = target_entry[1] if target_entry is not None else None
                if target_parser is None:
                    try:
                        target_parser = SiteParser()
                        target_parser.feed(target.read_text(encoding="utf-8"))
                    except (OSError, UnicodeDecodeError):
                        target_parser = None
                if target_parser is None or unquote(parsed.fragment) not in target_parser.ids:
                    errors.append(message("broken-fragment", f"Fragment '{reference}' does not resolve.", relative))

    manifest = _load_json_for_validation(manifest_path, errors) if manifest_path.is_file() else None
    validation = _load_json_for_validation(validation_path, errors) if validation_path.is_file() else None
    actual_files = {relative_site_path(site, path) for path in inventory_files}
    for asset in inventory_files:
        relative = relative_site_path(site, asset)
        if asset.suffix.lower() == ".css":
            try:
                css = asset.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                errors.append(message("invalid-css-encoding", "CSS must be UTF-8.", relative))
                continue
            if re.search(r"(?i)@import\b|expression\s*\(|javascript\s*:|behavior\s*:", css):
                errors.append(message("unsafe-css", "CSS contains an active or importing construct.", relative))
            for match in re.finditer(r"(?i)url\(\s*(['\"]?)(.*?)\1\s*\)", css):
                reference = match.group(2).strip()
                if reference.startswith("#"):
                    continue
                parsed = urlsplit(reference)
                if parsed.scheme or parsed.netloc or reference.startswith("//"):
                    errors.append(message("external-css-resource", f"CSS resource '{reference}' is not allowed.", relative))
                    continue
                target = _safe_relative_path(site, asset.parent, parsed.path)
                if target is None or not target.is_file():
                    errors.append(message("unsafe-css-resource", f"CSS resource '{reference}' is unsafe or missing.", relative))
        elif asset.suffix.lower() == ".svg":
            try:
                svg = asset.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                errors.append(message("invalid-svg-encoding", "SVG must be UTF-8.", relative))
                continue
            if re.search(r"(?i)<\s*(?:script|foreignObject|iframe|object|embed|form)\b", svg):
                errors.append(message("active-svg", "SVG contains active or embedded content.", relative))
            if re.search(r"(?i)\son[a-z]+\s*=", svg):
                errors.append(message("svg-event-handler", "SVG contains an inline event handler.", relative))
            for match in re.finditer(r"(?i)(?:href|xlink:href)\s*=\s*['\"]([^'\"]+)['\"]", svg):
                reference = match.group(1)
                if reference.startswith("#"):
                    continue
                parsed = urlsplit(reference)
                if parsed.scheme or parsed.netloc or reference.startswith("//"):
                    errors.append(message("external-svg-resource", f"SVG resource '{reference}' is not allowed.", relative))
                    continue
                target = _safe_relative_path(site, asset.parent, parsed.path)
                if target is None or not target.is_file():
                    errors.append(message("unsafe-svg-resource", f"SVG resource '{reference}' is unsafe or missing.", relative))
    if manifest is not None:
        errors.extend(validate_instance(
            manifest,
            load_json(SCHEMA_ROOT / "report-manifest-v1.schema.json"),
            path="report-manifest.json",
        ))
        required_manifest = {
            "manifestVersion", "reportKitVersion", "schemaVersion", "template", "reportId",
            "generatedAt", "dataAsOf", "classification", "pageCount", "itemCount", "files", "validation",
        }
        missing = sorted(required_manifest - set(manifest))
        for key in missing:
            errors.append(message("manifest-required", f"Manifest is missing '{key}'.", f"report-manifest.json.{key}"))
        files = manifest.get("files")
        declared: set[str] = set()
        if not isinstance(files, list) or not files:
            errors.append(message("manifest-files", "Manifest files must be a non-empty array.", "report-manifest.json.files"))
        else:
            for file_index, file_name in enumerate(files):
                if not isinstance(file_name, str):
                    errors.append(message("manifest-path", "Manifest file entries must be strings.", f"report-manifest.json.files[{file_index}]"))
                    continue
                target = _safe_relative_path(site, site, file_name)
                if target is None:
                    errors.append(message("manifest-path", f"Unsafe manifest path '{file_name}'.", f"report-manifest.json.files[{file_index}]"))
                    continue
                normalized = relative_site_path(site, target)
                if normalized in declared:
                    errors.append(message("manifest-duplicate-file", f"Duplicate manifest file '{normalized}'.", "report-manifest.json.files"))
                declared.add(normalized)
                if not target.is_file():
                    errors.append(message("manifest-file-missing", f"Manifest file '{file_name}' does not exist.", "report-manifest.json"))
            for undeclared in sorted(actual_files - declared):
                errors.append(message("manifest-undeclared-file", f"Generated file '{undeclared}' is not declared.", "report-manifest.json.files"))
            for absent in sorted(declared - actual_files):
                errors.append(message("manifest-file-missing", f"Declared file '{absent}' does not exist.", "report-manifest.json.files"))
        if manifest.get("pageCount") != len(html_files):
            errors.append(message("page-count-mismatch", f"Manifest pageCount is {manifest.get('pageCount')}; found {len(html_files)}.", "report-manifest.json"))
        if expected_item_count is not None and manifest.get("itemCount") != expected_item_count:
            errors.append(message("item-count-mismatch", f"Manifest itemCount is {manifest.get('itemCount')}; expected {expected_item_count}.", "report-manifest.json"))
        index_text = index.read_text(encoding="utf-8")
        index_entry = parsed_pages.get("index.html")
        artifact_counts = index_entry[1].item_counts if index_entry is not None else []
        if len(artifact_counts) != 1 or not artifact_counts[0].isdigit():
            errors.append(message(
                "item-count-evidence",
                "index.html must contain exactly one integer data-item-count value.",
                "index.html",
            ))
        elif manifest.get("itemCount") != int(artifact_counts[0]):
            errors.append(message(
                "item-count-mismatch",
                f"Manifest itemCount is {manifest.get('itemCount')}; index.html records {artifact_counts[0]}.",
                "report-manifest.json.itemCount",
            ))
        identity_values = {
            "reportId": manifest.get("reportId"),
            "classification": manifest.get("classification"),
        }
        for key, value in identity_values.items():
            if not isinstance(value, str) or not value.strip():
                errors.append(message("manifest-identity", f"Manifest {key} must be a non-empty string.", f"report-manifest.json.{key}"))
            elif escape(value) not in index_text:
                errors.append(message("manifest-identity-mismatch", f"Manifest {key} is not present in index.html.", f"report-manifest.json.{key}"))
        for key in ("generatedAt", "dataAsOf"):
            value = manifest.get(key)
            if not _is_datetime(value):
                errors.append(message("manifest-date-time", f"Manifest {key} must be an ISO-8601 date-time.", f"report-manifest.json.{key}"))
            elif escape(_format_datetime(value)) not in index_text:
                errors.append(message("manifest-identity-mismatch", f"Manifest {key} does not match index.html.", f"report-manifest.json.{key}"))
        template = manifest.get("template")
        if not isinstance(template, dict):
            errors.append(message("manifest-template", "Manifest template must be an object.", "report-manifest.json.template"))
        else:
            template_id = template.get("id")
            template_version = template.get("version")
            if (
                not isinstance(template_id, str)
                or not isinstance(template_version, str)
                or f'data-template="{escape(template_id)}"' not in index_text
                or f'data-template-version="{escape(template_version)}"' not in index_text
            ):
                errors.append(message("manifest-template-mismatch", "Manifest template identity does not match index.html.", "report-manifest.json.template"))
        errors.extend(verify_identity(manifest, site, inventory_files))

    if validation is not None:
        errors.extend(validate_instance(
            validation,
            load_json(SCHEMA_ROOT / "validation-report-v1.schema.json"),
            path="validation-report.json",
        ))
        if validation.get("reportVersion") != "1.0":
            errors.append(message("validation-report-version", "validation-report reportVersion must be '1.0'.", "validation-report.json.reportVersion"))
        summary = validation.get("summary")
        for key in ("errors", "warnings", "info"):
            if not isinstance(validation.get(key), list):
                errors.append(message("validation-report-shape", f"validation-report.{key} must be an array.", f"validation-report.json.{key}"))
        if not isinstance(summary, dict):
            errors.append(message("validation-report-shape", "validation-report.summary must be an object.", "validation-report.json.summary"))
        else:
            expected_counts = {
                "errorCount": len(validation.get("errors", [])) if isinstance(validation.get("errors"), list) else -1,
                "warningCount": len(validation.get("warnings", [])) if isinstance(validation.get("warnings"), list) else -1,
                "infoCount": len(validation.get("info", [])) if isinstance(validation.get("info"), list) else -1,
            }
            for key, expected in expected_counts.items():
                if summary.get(key) != expected:
                    errors.append(message("validation-count-mismatch", f"{key} does not match validation messages.", f"validation-report.json.summary.{key}"))
        reported_errors = validation.get("errors", [])
        reported_warnings = validation.get("warnings", [])
        derived_status = (
            "failed" if isinstance(reported_errors, list) and reported_errors
            else "passed-with-warnings" if isinstance(reported_warnings, list) and reported_warnings
            else "passed"
        )
        if validation.get("status") not in {"passed", "passed-with-warnings", "failed"}:
            errors.append(message("validation-status-invalid", "Validation status is not recognized.", "validation-report.json.status"))
        if isinstance(reported_errors, list) and reported_errors:
            errors.append(message("validation-reported-errors", "A validation report containing errors cannot permit publication.", "validation-report.json.errors"))
        if validation.get("status") != derived_status:
            errors.append(message("validation-status-mismatch", "Validation status does not match its error and warning counts.", "validation-report.json.status"))
        if isinstance(reported_warnings, list):
            warnings.extend(reported_warnings)
        reported_info = validation.get("info", [])
        if isinstance(reported_info, list):
            info.extend(reported_info)
        if manifest is not None and isinstance(manifest.get("validation"), dict):
            manifest_validation = manifest["validation"]
            pairs = {
                "status": validation.get("status"),
                "errors": len(validation.get("errors", [])) if isinstance(validation.get("errors"), list) else None,
                "warnings": len(validation.get("warnings", [])) if isinstance(validation.get("warnings"), list) else None,
                "info": len(validation.get("info", [])) if isinstance(validation.get("info"), list) else None,
            }
            for key, expected in pairs.items():
                if manifest_validation.get(key) != expected:
                    errors.append(message("manifest-validation-mismatch", f"Manifest validation {key} does not match validation-report.json.", f"report-manifest.json.validation.{key}"))
            if manifest_validation.get("status") not in {"passed", "passed-with-warnings"}:
                errors.append(message("manifest-validation-status", "Manifest validation status does not permit publication.", "report-manifest.json.validation.status"))
    return validation_report(errors, warnings, info)


def prepare_output_paths(
    output_path: Path,
    overwrite: bool,
) -> tuple[Path | None, Path | None, dict[str, Any]]:
    output_path = lexical_absolute_path(output_path)
    temporary = output_path.with_name(output_path.name + ".building")
    backup = output_path.with_name(output_path.name + ".previous")
    redirected = _first_reparse_component(output_path)
    if redirected is not None:
        return None, None, validation_report([message(
            "output-path-redirection",
            "Output path cannot contain a symbolic link, junction, or reparse point.",
            str(redirected),
        )])
    for path, code in ((temporary, "staging-exists"), (backup, "backup-exists")):
        if _path_lexists(path):
            return None, None, validation_report([message(
                code,
                f"Refusing to remove pre-existing path '{path}'. Resolve it explicitly before retrying.",
                str(path),
            )])
    if _path_lexists(output_path):
        if not output_path.is_dir():
            return None, None, validation_report([message(
                "output-not-directory",
                "Existing output must be a normal directory.",
                str(output_path),
            )])
        marker_path = output_path / OUTPUT_MARKER
        if _is_reparse_point(marker_path):
            return None, None, validation_report([message(
                "output-marker-redirection",
                "ReportKit ownership marker cannot be a symbolic link, junction, or reparse point.",
                str(marker_path),
            )])
        if not marker_path.is_file():
            return None, None, validation_report([message(
                "output-not-owned",
                "Existing output has no ReportKit ownership marker and will not be replaced.",
                str(output_path),
            )])
        marker = _load_json_for_validation(marker_path, [])
        if marker is None or marker.get("markerVersion") != "1.0" or marker.get("managedBy") != "ReportKit":
            return None, None, validation_report([message(
                "output-marker-invalid",
                "Existing output has an invalid ReportKit ownership marker.",
                str(marker_path),
            )])
        if not overwrite:
            return None, None, validation_report([message(
                "overwrite-required",
                "Existing ReportKit output requires explicit overwrite approval.",
                str(output_path),
            )])
    return temporary, backup, validation_report()


def replace_output(temporary: Path, output_path: Path, backup: Path) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    had_output = _path_lexists(output_path)
    moved_to_backup = False
    try:
        if had_output:
            output_path.rename(backup)
            moved_to_backup = True
        temporary.rename(output_path)
    except OSError:
        if moved_to_backup and not _path_lexists(output_path) and _path_lexists(backup):
            backup.rename(output_path)
        raise
    if moved_to_backup and _path_lexists(backup):
        try:
            shutil.rmtree(backup)
        except OSError as exception:
            warnings.append(message(
                "backup-cleanup-failed",
                f"New output is active, but the previous-output backup could not be fully removed: {exception}",
                str(backup),
            ))
    return warnings


def build_site(
    model_path: Path,
    config_path: Path,
    capability_path: Path,
    output_path: Path,
    overwrite: bool = False,
) -> dict[str, Any]:
    output_path = lexical_absolute_path(output_path)
    input_errors: list[dict[str, str]] = []
    model = _load_json_for_validation(model_path, input_errors)
    config = _load_json_for_validation(config_path, input_errors)
    capability = _load_json_for_validation(capability_path, input_errors)
    if input_errors or model is None or config is None or capability is None:
        return validation_report(input_errors)
    model_report = validate_model(model, capability)
    config_report = validate_config(config, capability)
    combined_input_report = merge_reports(model_report, config_report)
    if combined_input_report["errors"]:
        return combined_input_report
    if capability["id"] not in BUILTIN_TEMPLATE_IDS:
        return validation_report([message(
            "template-not-implemented",
            f"Template '{capability['id']}' is not a supported built-in renderer.",
            "template.id",
        )])

    temporary, backup, output_report = prepare_output_paths(output_path, overwrite)
    if output_report["errors"]:
        return output_report
    assert temporary is not None and backup is not None
    if capability["id"] == "executive-health":
        pages = {"index.html": render_executive_health(model, config)}
    else:
        from builtin_renderers import render_builtin_pages
        pages = render_builtin_pages(capability["id"], model, config)
    if "index.html" not in pages or any(
        not isinstance(name, str) or not name.endswith(".html")
        or "/" in name or "\\" in name or _safe_relative_path(temporary, temporary, name) is None
        for name in pages
    ):
        return validation_report([message("renderer-page-path", "Renderer must return safe, flat HTML filenames with index.html.")])
    temporary.mkdir(parents=True)
    for name, html_text in sorted(pages.items()):
        (temporary / name).write_text(html_text, encoding="utf-8", newline="\n")
    write_json(temporary / OUTPUT_MARKER, {
        "markerVersion": "1.0",
        "managedBy": "ReportKit",
        "reportId": model["report"]["id"],
    })
    preliminary = merge_reports(model_report, config_report)
    write_json(temporary / "validation-report.json", preliminary)
    manifest = {
        "manifestVersion": "1.0",
        "reportKitVersion": REPORTKIT_VERSION,
        "schemaVersion": model["schemaVersion"],
        "template": {
            "id": capability["id"],
            "version": capability["version"],
            "kind": "built-in",
            "source": "repository",
            "digest": f"sha256:{hashlib.sha256(normalize_text_bytes(capability_path.read_bytes())).hexdigest()}",
        },
        "reportId": model["report"]["id"],
        "generatedAt": model["report"]["generatedAt"],
        "dataAsOf": model["report"]["dataAsOf"],
        "classification": model["report"]["classification"],
        "pageCount": len(pages),
        "itemCount": len(model.get("items", [])),
        "files": [OUTPUT_MARKER, *sorted(pages), "report-manifest.json", "validation-report.json"],
        "validation": {
            "status": preliminary["status"],
            "errors": preliminary["summary"]["errorCount"],
            "warnings": preliminary["summary"]["warningCount"],
            "info": preliminary["summary"]["infoCount"],
        },
    }
    write_json(temporary / "report-manifest.json", manifest)
    from artifact_identity import make_reproducibility
    manifest["reproducibility"] = make_reproducibility(model, config, temporary)
    write_json(temporary / "report-manifest.json", manifest)

    site_report = validate_site(temporary, len(model.get("items", [])))
    final_report = merge_reports(model_report, site_report)
    manifest["validation"] = {
        "status": final_report["status"],
        "errors": final_report["summary"]["errorCount"],
        "warnings": final_report["summary"]["warningCount"],
        "info": final_report["summary"]["infoCount"],
    }
    write_json(temporary / "validation-report.json", final_report)
    manifest["reproducibility"] = make_reproducibility(model, config, temporary)
    write_json(temporary / "report-manifest.json", manifest)
    final_site_report = validate_site(temporary, len(model.get("items", [])))
    if final_site_report["errors"]:
        shutil.rmtree(temporary)
        return merge_reports(final_report, final_site_report)
    if final_report["errors"]:
        shutil.rmtree(temporary)
        return final_report

    try:
        replacement_warnings = replace_output(temporary, output_path, backup)
    except OSError as exception:
        return validation_report([message("output-replacement-failed", f"Could not replace output safely: {exception}", str(output_path))])
    if replacement_warnings:
        final_report = merge_reports(final_report, validation_report(warnings=replacement_warnings))
        manifest["validation"] = {
            "status": final_report["status"],
            "errors": final_report["summary"]["errorCount"],
            "warnings": final_report["summary"]["warningCount"],
            "info": final_report["summary"]["infoCount"],
        }
        write_json(output_path / "validation-report.json", final_report)
        write_json(output_path / "report-manifest.json", manifest)
    return final_report
