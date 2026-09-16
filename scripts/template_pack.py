"""Dependency-free validation and rendering for declarative ReportKit template packs."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import stat
import time
import zipfile
from collections import Counter
from datetime import datetime, timedelta
from html import escape
from pathlib import Path, PurePosixPath
from typing import Any

from reportkit_engine import (
    REPORTKIT_VERSION,
    _format_datetime,
    _freshness,
    _load_json_for_validation,
    _owner_label,
    _priority_sort,
    OUTPUT_MARKER,
    load_json,
    lexical_absolute_path,
    merge_reports,
    message,
    normalize_text_bytes,
    prepare_output_paths,
    replace_output,
    validate_config,
    validate_model,
    validate_site,
    validation_report,
    write_json,
)
from json_schema import validate_instance, validate_schema_definition
from artifact_identity import make_reproducibility, validate_capabilities

MAX_FILES = 100
MAX_TOTAL_BYTES = 5 * 1024 * 1024
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_IMAGE_BYTES = 1024 * 1024
MAX_PACK_SECONDS = 10.0
ALLOWED_SUFFIXES = {".json", ".md", ".txt", ".png", ".webp"}
PROHIBITED_SUFFIXES = {
    ".html", ".htm", ".css", ".js", ".mjs", ".cjs", ".svg", ".zip", ".tar", ".gz",
    ".7z", ".rar", ".exe", ".dll", ".bat", ".cmd", ".ps1", ".py", ".sh",
}
REQUIRED_FILES = {
    "template.json",
    "config.schema.json",
    "layout.json",
    "theme.json",
    "README.md",
    "LICENSE",
    "examples/minimum.json",
    "examples/canonical-report.json",
    "examples/configuration.json",
    "tests/cases.json",
}
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
TEMPLATE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*$")
SAFE_PATH_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
COMPONENTS: dict[str, dict[str, set[str]]] = {
    "report-masthead": {"sources": set(), "variants": set(), "selections": set()},
    "overall-status": {"sources": set(), "variants": set(), "selections": set()},
    "freshness-panel": {"sources": set(), "variants": set(), "selections": set()},
    "metric-grid": {"sources": {"metrics"}, "variants": {"four-up", "three-up"}, "selections": set()},
    "trend-visualization": {"sources": {"trends"}, "variants": {"bars"}, "selections": set()},
    "signal-list": {"sources": {"highlights"}, "variants": set(), "selections": set()},
    "attention-table": {
        "sources": {"items"},
        "variants": set(),
        "selections": {"leadership-attention", "all-open", "overdue", "blocked", "due-in-seven-days"},
    },
    "group-card-grid": {"sources": {"groups"}, "variants": set(), "selections": set()},
    "empty-state": {"sources": set(), "variants": set(), "selections": set()},
    "stale-data-warning": {"sources": set(), "variants": set(), "selections": set()},
    "partial-coverage-warning": {"sources": set(), "variants": set(), "selections": set()},
    "validation-warning-banner": {"sources": set(), "variants": set(), "selections": set()},
    "report-footer": {"sources": set(), "variants": set(), "selections": set()},
}


def _safe_pack_path(name: str) -> bool:
    if not name or "\\" in name or "\x00" in name:
        return False
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and not any(":" in part for part in path.parts)


def _load_folder(folder: Path, deadline: float | None = None) -> tuple[dict[str, bytes], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    files: dict[str, bytes] = {}
    for path in folder.rglob("*"):
        if deadline is not None:
            _check_pack_budget(deadline)
        relative = path.relative_to(folder).as_posix()
        if path.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(path)):
            errors.append(message("pack-symlink", "Template packs cannot contain symbolic links or junctions.", relative))
            continue
        if path.is_file():
            if path.stat().st_size > MAX_FILE_BYTES:
                errors.append(message("pack-file-size", "Template-pack file exceeds the size limit.", relative))
                continue
            files[relative] = path.read_bytes()
    return files, errors


def _load_zip(archive: Path, deadline: float | None = None) -> tuple[dict[str, bytes], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    files: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(archive) as package:
            entries = [entry for entry in package.infolist() if not entry.is_dir()]
            if len(entries) > MAX_FILES:
                errors.append(message("pack-file-count", f"Template pack exceeds {MAX_FILES} files."))
            for entry in entries[: MAX_FILES + 1]:
                if deadline is not None:
                    _check_pack_budget(deadline)
                name = entry.filename
                mode = entry.external_attr >> 16
                if stat.S_ISLNK(mode):
                    errors.append(message("pack-symlink", "Template packs cannot contain symbolic links.", name))
                    continue
                if not _safe_pack_path(name):
                    errors.append(message("pack-path", "Unsafe archive entry path.", name))
                    continue
                if name in files:
                    errors.append(message("pack-duplicate-file", "Duplicate archive entry.", name))
                    continue
                if entry.file_size > MAX_FILE_BYTES:
                    errors.append(message("pack-file-size", "Template-pack file exceeds the size limit.", name))
                    continue
                files[name] = package.read(entry)
    except (OSError, RuntimeError, zipfile.BadZipFile) as exception:
        errors.append(message("pack-archive", f"Cannot read template archive: {exception}", archive.name))
    return files, errors


def load_pack(path: Path, deadline: float | None = None) -> tuple[dict[str, bytes], list[dict[str, str]]]:
    if path.is_dir():
        return _load_folder(path, deadline)
    if path.is_file() and path.suffix.lower() == ".zip":
        return _load_zip(path, deadline)
    return {}, [message("pack-location", "Template pack must be a local folder or ZIP archive.", str(path))]


def _normalize_pack_root(files: dict[str, bytes]) -> dict[str, bytes]:
    if REQUIRED_FILES.issubset(files):
        return files
    roots = {PurePosixPath(name).parts[0] for name in files if len(PurePosixPath(name).parts) > 1}
    if len(roots) != 1:
        return files
    root = next(iter(roots))
    normalized = {
        PurePosixPath(*PurePosixPath(name).parts[1:]).as_posix(): content
        for name, content in files.items()
        if PurePosixPath(name).parts[0] == root and len(PurePosixPath(name).parts) > 1
    }
    return normalized if REQUIRED_FILES.issubset(normalized) else files


def pack_digest(files: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name in sorted(files):
        content = files[name]
        if PurePosixPath(name).suffix.lower() in {".json", ".md", ".txt"} or not PurePosixPath(name).suffix:
            content = normalize_text_bytes(content)
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def _json_file(files: dict[str, bytes], name: str, errors: list[dict[str, str]]) -> dict[str, Any] | None:
    from reportkit_engine import load_json_bytes

    try:
        if len(files[name]) > MAX_FILE_BYTES:
            raise ValueError("JSON document exceeds the template-pack byte limit.")
        value = load_json_bytes(files[name], name)
        if not isinstance(value, dict):
            raise ValueError("JSON document must contain an object.")
    except (KeyError, ValueError, RecursionError) as exception:
        errors.append(message("pack-json", f"Invalid JSON: {exception}", name))
        return None
    return value


def _version_tuple(value: str) -> tuple[int, int, int] | None:
    match = SEMVER.fullmatch(value)
    return tuple(map(int, match.groups())) if match else None


def _validate_template(template: dict[str, Any], errors: list[dict[str, str]]) -> None:
    allowed = {
        "contractVersion", "id", "displayName", "version", "description", "audience",
        "primaryDecision", "supportedSchemaVersions", "requiredSections", "requiredFields",
        "optionalSections", "supportedPageTypes", "features", "compatibility",
        "implementationCapabilities", "designCapabilities",
    }
    for key in sorted(set(template) - allowed):
        errors.append(message("pack-template-property", f"Unknown template property '{key}'.", f"template.json.{key}"))
    required = allowed - {"description", "optionalSections", "features", "implementationCapabilities", "designCapabilities"}
    for key in sorted(required):
        if key not in template:
            errors.append(message("pack-template-required", f"Missing template property '{key}'.", f"template.json.{key}"))
    template_id = template.get("id")
    if not isinstance(template_id, str) or not TEMPLATE_ID.fullmatch(template_id) or template_id.startswith("reportkit/"):
        errors.append(message("pack-template-id", "Custom template ID must be a lowercase namespaced ID and cannot use reportkit/*.", "template.json.id"))
    version = template.get("version")
    if not isinstance(version, str) or _version_tuple(version) is None:
        errors.append(message("pack-template-version", "Template version must be an exact semantic version.", "template.json.version"))
    if template.get("contractVersion") != "1.0":
        errors.append(message("pack-contract-version", "contractVersion must be '1.0'.", "template.json.contractVersion"))
    for key in ("displayName", "audience", "primaryDecision"):
        if not isinstance(template.get(key), str) or not template[key].strip():
            errors.append(message("pack-template-string", f"{key} must be a non-empty string.", f"template.json.{key}"))
    if "1.0" not in template.get("supportedSchemaVersions", []):
        errors.append(message("pack-schema-compatibility", "Template must support canonical schema 1.0.", "template.json.supportedSchemaVersions"))
    for key in ("requiredSections", "requiredFields", "optionalSections", "supportedPageTypes"):
        value = template.get(key, [])
        if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
            errors.append(message("pack-template-array", f"{key} must be an array of non-empty strings.", f"template.json.{key}"))
        elif len(value) != len(set(value)):
            errors.append(message("pack-template-duplicate", f"{key} cannot contain duplicates.", f"template.json.{key}"))
    features = template.get("implementationCapabilities", template.get("features"))
    if not isinstance(features, dict):
        errors.append(message("pack-features", "Runtime capabilities must be an object.", "template.json.implementationCapabilities"))
    else:
        if features.get("scriptFree") is not True:
            errors.append(message("pack-script-free", "Declarative templates must be script-free.", "template.json.implementationCapabilities.scriptFree"))
        if features.get("multiPage") is not False:
            errors.append(message("pack-implementation-scope", "The declarative renderer implements single-page output only.", "template.json.implementationCapabilities.multiPage"))
    compatibility = template.get("compatibility")
    minimum = compatibility.get("minimumReportKitVersion") if isinstance(compatibility, dict) else None
    minimum_tuple = _version_tuple(minimum) if isinstance(minimum, str) else None
    current_tuple = _version_tuple(REPORTKIT_VERSION)
    if minimum_tuple is None:
        errors.append(message("pack-compatibility", "minimumReportKitVersion must be an exact semantic version.", "template.json.compatibility.minimumReportKitVersion"))
    elif current_tuple is not None and minimum_tuple > current_tuple:
        errors.append(message("pack-incompatible", f"Template requires ReportKit {minimum} or later.", "template.json.compatibility.minimumReportKitVersion"))


def _validate_layout(layout: dict[str, Any], errors: list[dict[str, str]]) -> None:
    if set(layout) - {"layoutVersion", "pages"}:
        errors.append(message("pack-layout-property", "layout.json contains unknown properties.", "layout.json"))
    if layout.get("layoutVersion") != "1.0":
        errors.append(message("pack-layout-version", "layoutVersion must be '1.0'.", "layout.json.layoutVersion"))
    pages = layout.get("pages")
    if not isinstance(pages, list) or not pages:
        errors.append(message("pack-layout-pages", "layout.pages must be a non-empty array.", "layout.json.pages"))
        return
    page_ids: set[str] = set()
    page_paths: set[str] = set()
    for page_index, page in enumerate(pages):
        path = f"layout.json.pages[{page_index}]"
        if not isinstance(page, dict):
            errors.append(message("pack-layout-page", "Page must be an object.", path))
            continue
        allowed_page = {"id", "path", "repeatFor", "pathPattern", "sections"}
        for key in sorted(set(page) - allowed_page):
            errors.append(message("pack-layout-property", f"Unknown page property '{key}'.", f"{path}.{key}"))
        page_id = page.get("id")
        if not isinstance(page_id, str) or not SAFE_PATH_ID.fullmatch(page_id):
            errors.append(message("pack-page-id", "Page ID must be lowercase and path-safe.", f"{path}.id"))
        elif page_id in page_ids:
            errors.append(message("pack-page-duplicate", f"Duplicate page ID '{page_id}'.", f"{path}.id"))
        else:
            page_ids.add(page_id)
        page_path = page.get("path")
        pattern = page.get("pathPattern")
        selected_path = page_path or pattern
        if not isinstance(selected_path, str) or not _safe_pack_path(selected_path.replace("{id}", "sample")) or not selected_path.endswith(".html"):
            errors.append(message("pack-page-path", "Page path must be a contained HTML path.", path))
        elif selected_path in page_paths:
            errors.append(message("pack-page-duplicate", f"Duplicate page path '{selected_path}'.", path))
        else:
            page_paths.add(selected_path)
        if pattern is not None and pattern.count("{id}") != 1:
            errors.append(message("pack-page-pattern", "pathPattern must contain exactly one {id} token.", f"{path}.pathPattern"))
        if page.get("repeatFor") not in (None, "groups"):
            errors.append(message("pack-repeat", "The MVP only supports repeatFor: groups.", f"{path}.repeatFor"))
        sections = page.get("sections")
        if not isinstance(sections, list) or not sections:
            errors.append(message("pack-sections", "Page sections must be a non-empty array.", f"{path}.sections"))
            continue
        for section_index, section in enumerate(sections):
            section_path = f"{path}.sections[{section_index}]"
            if not isinstance(section, dict):
                errors.append(message("pack-section", "Section must be an object.", section_path))
                continue
            for key in sorted(set(section) - {"component", "source", "variant", "selection", "linkTo"}):
                errors.append(message("pack-section-property", f"Unknown section property '{key}'.", f"{section_path}.{key}"))
            component = section.get("component")
            specification = COMPONENTS.get(component)
            if specification is None:
                errors.append(message("pack-component", f"Unknown component '{component}'.", f"{section_path}.component"))
                continue
            source = section.get("source")
            if specification["sources"] and source not in specification["sources"]:
                errors.append(message("pack-component-source", f"Component '{component}' requires one of {sorted(specification['sources'])}.", f"{section_path}.source"))
            if not specification["sources"] and source is not None:
                errors.append(message("pack-component-source", f"Component '{component}' does not accept a source.", f"{section_path}.source"))
            variant = section.get("variant")
            if variant is not None and variant not in specification["variants"]:
                errors.append(message("pack-component-variant", f"Unsupported variant '{variant}'.", f"{section_path}.variant"))
            selection = section.get("selection")
            if selection is not None and selection not in specification["selections"]:
                errors.append(message("pack-component-selection", f"Unsupported selection '{selection}'.", f"{section_path}.selection"))
    if "index.html" not in page_paths:
        errors.append(message("pack-index", "A declarative pack must define index.html.", "layout.json.pages"))


def _validate_theme(theme: dict[str, Any], errors: list[dict[str, str]]) -> None:
    if set(theme) - {"themeVersion", "name", "tokens", "terminology"}:
        errors.append(message("pack-theme-property", "theme.json contains unknown properties.", "theme.json"))
    if theme.get("themeVersion") != "1.0":
        errors.append(message("pack-theme-version", "themeVersion must be '1.0'.", "theme.json.themeVersion"))
    if not isinstance(theme.get("name"), str) or not theme["name"].strip():
        errors.append(message("pack-theme-name", "Theme name must be a non-empty string.", "theme.json.name"))
    tokens = theme.get("tokens")
    allowed_tokens = {"primary", "accent", "canvas", "surface", "fontFamily"}
    if not isinstance(tokens, dict):
        errors.append(message("pack-theme-tokens", "tokens must be an object.", "theme.json.tokens"))
    else:
        for key in sorted(set(tokens) - allowed_tokens):
            errors.append(message("pack-theme-token", f"Unknown theme token '{key}'.", f"theme.json.tokens.{key}"))
        for key in ("primary", "accent", "canvas", "surface"):
            if not isinstance(tokens.get(key), str) or not COLOR.fullmatch(tokens[key]):
                errors.append(message("pack-theme-color", f"{key} must be a six-digit hexadecimal color.", f"theme.json.tokens.{key}"))
        if tokens.get("fontFamily") != "system":
            errors.append(message("pack-theme-font", "The MVP only permits the system font stack.", "theme.json.tokens.fontFamily"))
    terminology = theme.get("terminology", {})
    if not isinstance(terminology, dict):
        errors.append(message("pack-terminology", "terminology must be an object.", "theme.json.terminology"))
    else:
        allowed_terms = {"group", "item", "accountableOwner", "actionOwner"}
        for key in sorted(set(terminology) - allowed_terms):
            errors.append(message("pack-terminology-key", f"Unknown terminology key '{key}'.", f"theme.json.terminology.{key}"))
        for key, value in terminology.items():
            if not isinstance(value, str) or not 1 <= len(value) <= 60 or re.search(r"[<>]", value):
                errors.append(message("pack-terminology-value", "Terminology must be plain text from 1 to 60 characters.", f"theme.json.terminology.{key}"))


class _PackBudgetExceeded(Exception):
    pass


def _check_pack_budget(deadline: float) -> None:
    if time.monotonic() >= deadline:
        raise _PackBudgetExceeded


def validate_pack(path: Path) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Validate within a cooperative deadline, not a hard filesystem/OS timeout."""
    deadline = time.monotonic() + MAX_PACK_SECONDS
    try:
        return _validate_pack(path, deadline)
    except _PackBudgetExceeded:
        return validation_report([message(
            "pack-budget",
            "Template-pack validation exceeded its cooperative time budget.",
            "template-pack",
        )]), None


def _validate_pack(path: Path, deadline: float) -> tuple[dict[str, Any], dict[str, Any] | None]:
    _check_pack_budget(deadline)
    files, initial_errors = load_pack(path, deadline)
    _check_pack_budget(deadline)
    files = _normalize_pack_root(files)
    errors = list(initial_errors)
    if len(files) > MAX_FILES:
        errors.append(message("pack-file-count", f"Template pack exceeds {MAX_FILES} files."))
    if sum(len(content) for content in files.values()) > MAX_TOTAL_BYTES:
        errors.append(message("pack-total-size", "Template pack exceeds the total size limit."))
    for required in sorted(REQUIRED_FILES - set(files)):
        errors.append(message("pack-required-file", f"Missing required file '{required}'.", required))
    for name, content in files.items():
        _check_pack_budget(deadline)
        if not _safe_pack_path(name):
            errors.append(message("pack-path", "Unsafe template-pack path.", name))
        suffix = PurePosixPath(name).suffix.lower()
        if suffix in PROHIBITED_SUFFIXES or (suffix and suffix not in ALLOWED_SUFFIXES):
            errors.append(message("pack-file-type", f"File type '{suffix or '[none]'}' is not allowed.", name))
        if len(content) > MAX_FILE_BYTES or (suffix in {".png", ".webp"} and len(content) > MAX_IMAGE_BYTES):
            errors.append(message("pack-file-size", "Template-pack file exceeds the size limit.", name))
        if suffix == ".png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
            errors.append(message("pack-image-type", "PNG asset content does not match its extension.", name))
        if suffix == ".webp" and not (content.startswith(b"RIFF") and content[8:12] == b"WEBP"):
            errors.append(message("pack-image-type", "WebP asset content does not match its extension.", name))
        if suffix in {".json", ".md", ".txt"} or not suffix:
            text = content.decode("utf-8", errors="ignore")
            if re.search(r"(?i)<\s*(?:script|style|iframe|object|embed|form|base)\b", text):
                errors.append(message("pack-active-content", "Template packs cannot contain active HTML or CSS.", name))
            if re.search(r"!\[[^\]]*\]\(\s*(?:https?:)?//", text, re.IGNORECASE):
                errors.append(message("pack-remote-asset", "Template-pack documentation cannot embed remote assets.", name))
    def read_member(name: str) -> dict[str, Any] | None:
        _check_pack_budget(deadline)
        value = _json_file(files, name, errors)
        _check_pack_budget(deadline)
        return value

    template = read_member("template.json")
    layout = read_member("layout.json")
    theme = read_member("theme.json")
    config_schema = read_member("config.schema.json")
    minimum = read_member("examples/minimum.json")
    canonical = read_member("examples/canonical-report.json")
    configuration = read_member("examples/configuration.json")
    cases = read_member("tests/cases.json")
    custom_schema_errors: list[dict[str, str]] = []
    template_usable = False
    if config_schema is not None:
        _check_pack_budget(deadline)
        custom_schema_errors = validate_schema_definition(config_schema)
        _check_pack_budget(deadline)
        for issue in custom_schema_errors:
            errors.append(message(
                f"pack-custom-{issue['code']}",
                issue["message"],
                f"config.schema.json:{issue.get('path', '')}",
            ))
    if template is not None:
        capability_errors = validate_capabilities(template)
        errors.extend(capability_errors)
        _check_pack_budget(deadline)
        if not capability_errors:
            previous_error_count = len(errors)
            _validate_template(template, errors)
            template_usable = len(errors) == previous_error_count
    if layout is not None:
        _check_pack_budget(deadline)
        layout_errors = validate_instance(
            layout,
            load_json(Path(__file__).resolve().parents[1] / "schema" / "template-layout-v1.schema.json"),
            path="layout.json",
        )
        errors.extend(layout_errors)
        for issue in layout_errors:
            if issue.get("path", "").endswith(".component"):
                errors.append(message("pack-component", issue["message"], issue["path"]))
        _check_pack_budget(deadline)
        if not layout_errors:
            _validate_layout(layout, errors)
    if theme is not None:
        _check_pack_budget(deadline)
        theme_errors = validate_instance(
            theme,
            load_json(Path(__file__).resolve().parents[1] / "schema" / "template-theme-v1.schema.json"),
            path="theme.json",
        )
        errors.extend(theme_errors)
        for issue in theme_errors:
            if ".tokens." in issue.get("path", ""):
                errors.append(message("pack-theme-color", issue["message"], issue["path"]))
        _check_pack_budget(deadline)
        if not theme_errors:
            _validate_theme(theme, errors)
    if cases is not None and not isinstance(cases.get("cases"), list):
        errors.append(message("pack-tests", "tests/cases.json must contain a cases array.", "tests/cases.json.cases"))
    for name in ("README.md", "LICENSE"):
        if name in files and not files[name].decode("utf-8", errors="ignore").strip():
            errors.append(message("pack-document", f"{name} cannot be empty.", name))
    if template_usable:
        for name, model in (("examples/minimum.json", minimum), ("examples/canonical-report.json", canonical)):
            _check_pack_budget(deadline)
            if model is not None:
                report = validate_model(model, template)
                _check_pack_budget(deadline)
                for issue in report["errors"]:
                    errors.append(message(f"pack-example-{issue['code']}", issue["message"], f"{name}:{issue.get('path', '')}"))
        if configuration is not None:
            _check_pack_budget(deadline)
            report = validate_config(configuration, template)
            _check_pack_budget(deadline)
            for issue in report["errors"]:
                errors.append(message(f"pack-config-{issue['code']}", issue["message"], f"examples/configuration.json:{issue.get('path', '')}"))
            if config_schema is not None and not custom_schema_errors:
                _check_pack_budget(deadline)
                for issue in validate_instance(configuration, config_schema, path="examples/configuration.json"):
                    errors.append(message(f"pack-custom-{issue['code']}", issue["message"], issue["path"]))
                _check_pack_budget(deadline)
        if cases is not None and isinstance(cases.get("cases"), list):
            for case_index, case in enumerate(cases["cases"]):
                _check_pack_budget(deadline)
                case_path = f"tests/cases.json.cases[{case_index}]"
                if not isinstance(case, dict) or not isinstance(case.get("expected"), str):
                    errors.append(message("pack-case", "Each case requires an expected result.", case_path))
                    continue
                case_model: dict[str, Any] | None = None
                if isinstance(case.get("input"), str):
                    case_model = read_member(case["input"])
                elif isinstance(case.get("mutation"), str) and canonical is not None:
                    case_model = copy.deepcopy(canonical)
                    match = re.fullmatch(r"remove ([A-Za-z0-9_.]+)", case["mutation"])
                    if match:
                        parts = match.group(1).split(".")
                        current: Any = case_model
                        for part in parts[:-1]:
                            current = current.get(part) if isinstance(current, dict) else None
                        if isinstance(current, dict):
                            current.pop(parts[-1], None)
                    else:
                        errors.append(message("pack-case-mutation", "Unsupported case mutation.", f"{case_path}.mutation"))
                else:
                    errors.append(message("pack-case-input", "Case requires input or a supported mutation.", case_path))
                if case_model is not None:
                    _check_pack_budget(deadline)
                    result = validate_model(case_model, template)
                    _check_pack_budget(deadline)
                    actual = "failed" if result["errors"] else "passed"
                    if actual != case["expected"]:
                        errors.append(message(
                            "pack-case-result",
                            f"Case expected {case['expected']} but produced {actual}.",
                            case_path,
                        ))

    _check_pack_budget(deadline)
    report = validation_report(errors)
    if report["errors"]:
        return report, None
    digest = pack_digest(files)
    _check_pack_budget(deadline)
    return report, {
        "files": files,
        "template": template,
        "layout": layout,
        "theme": theme,
        "configSchema": config_schema,
        "configuration": configuration,
        "digest": digest,
    }


def validate_lock(lock_path: Path, pack: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    try:
        lock = load_json(lock_path)
    except (OSError, ValueError, json.JSONDecodeError) as exception:
        return validation_report([message("template-lock", f"Cannot read template lock: {exception}", str(lock_path))])
    if lock.get("lockVersion") != "1.0" or not isinstance(lock.get("templates"), list):
        return validation_report([message("template-lock", "Invalid reportkit.lock.json structure.", str(lock_path))])
    matches = [
        entry for entry in lock["templates"]
        if isinstance(entry, dict)
        and entry.get("id") == pack["template"]["id"]
        and entry.get("version") == pack["template"]["version"]
    ]
    if len(matches) != 1:
        errors.append(message(
            "template-lock-entry",
            "The selected template ID and version must have exactly one lock entry.",
            str(lock_path),
        ))
    else:
        entry = matches[0]
        if entry.get("kind") != "declarative" or entry.get("source") != "project":
            errors.append(message("template-lock-trust", "Lock entry trust metadata is invalid.", str(lock_path)))
        if entry.get("digest") != pack["digest"]:
            errors.append(message(
                "template-lock-digest",
                "Template bytes differ from the locked digest and require explicit revalidation and relocking.",
                str(lock_path),
            ))
    return validation_report(errors)


def _render_component(component: dict[str, Any], model: dict[str, Any], terms: dict[str, str]) -> str:
    name = component["component"]
    if name in {"report-masthead", "freshness-panel", "report-footer"}:
        return ""
    if name == "overall-status":
        report = model["report"]
        return (
            '<section class="card status"><p class="eyebrow">Overall status</p>'
            f"<h2>{escape(report.get('statusLabel', report.get('status', 'unknown').title()))}</h2>"
            f"<p>{escape(report.get('statusSummary', ''))}</p></section>"
        )
    if name == "metric-grid":
        metrics = sorted(model.get("metrics", []), key=lambda item: (item.get("order", 9999), item["id"]))[:4]
        cards = "".join(
            f'<article class="metric"><p>{escape(metric["label"])}</p><strong>{escape(str(metric["value"]))}</strong>'
            f'<span>{escape(metric["unit"])}</span><small>{escape(metric.get("description", ""))}</small></article>'
            for metric in metrics
        )
        return f'<section class="metrics" aria-label="Key metrics">{cards}</section>'
    if name == "signal-list":
        rows = "".join(
            f'<li><strong>{escape(item["title"])}</strong><span>{escape(item.get("summary", ""))}</span></li>'
            for item in sorted(model.get("highlights", []), key=lambda item: (item.get("order", 9999), item["id"]))[:6]
        )
        return f'<section class="card"><h2>Confirmed signals</h2><ul class="signals">{rows or "<li>No signals supplied.</li>"}</ul></section>'
    if name == "attention-table":
        selection = component.get("selection", "leadership-attention")
        report_date = datetime.fromisoformat(model["report"]["generatedAt"].replace("Z", "+00:00")).date()
        items = []
        for item in model.get("items", []):
            status = item.get("status")
            due = datetime.strptime(item["dueDate"], "%Y-%m-%d").date() if item.get("dueDate") else None
            include = (
                selection == "leadership-attention" and item.get("priority") in {"critical", "high"}
                or selection == "all-open" and status not in {"complete", "passed"}
                or selection == "overdue" and status not in {"complete", "passed"} and due is not None and due < report_date
                or selection == "blocked" and status not in {"complete", "passed"} and (status == "blocked" or bool(item.get("blocker")))
                or selection == "due-in-seven-days" and status not in {"complete", "passed"} and due is not None and report_date <= due <= report_date + timedelta(days=7)
            )
            if include:
                items.append(item)
        items = sorted(items, key=_priority_sort)
        rows = "".join(
            f'<tr><td><strong>{escape(item["title"])}</strong><span>{escape(item.get("summary", ""))}</span></td>'
            f'<td>{escape(item.get("priority", "unknown"))}</td><td>{escape(_owner_label(item.get("accountableOwner")))}</td>'
            f'<td>{escape(str(item.get("dueDate") or "Not set"))}</td><td>{escape(item.get("nextAction") or "Review required")}</td></tr>'
            for item in items
        )
        item_term = escape(terms.get("item", "Item"))
        return f'<section class="card table-card"><h2>{item_term} attention</h2><table><thead><tr><th>{item_term}</th><th>Priority</th><th>Owner</th><th>Due</th><th>Next action</th></tr></thead><tbody>{rows}</tbody></table></section>'
    if name == "group-card-grid":
        cards = "".join(
            f'<article class="group"><span>{escape(group.get("status", "unknown"))}</span><h3>{escape(group["label"])}</h3>'
            f'<p>{escape(group.get("summary", ""))}</p></article>'
            for group in sorted(model.get("groups", []), key=lambda item: (item.get("order", 9999), item["id"]))
        )
        return f'<section class="card"><h2>{escape(terms.get("group", "Group"))} overview</h2><div class="groups">{cards}</div></section>'
    if name == "trend-visualization":
        trend = next(iter(sorted(model.get("trends", []), key=lambda item: (item.get("order", 9999), item["id"]))), None)
        if not trend:
            return '<section class="card"><h2>Trend</h2><p>No trend history supplied.</p></section>'
        values = ", ".join(f'{escape(item["date"])}: {escape(str(item["value"]))}' for item in trend["observations"])
        return f'<section class="card"><h2>{escape(trend["label"])}</h2><p>{values}</p></section>'
    if name in {"empty-state", "stale-data-warning", "partial-coverage-warning", "validation-warning-banner"}:
        return f'<section class="notice">{escape(name.replace("-", " ").title())}</section>'
    raise ValueError(f"Unsupported declarative component: {name}")


def render_pack(pack: dict[str, Any], model: dict[str, Any], config: dict[str, Any]) -> str:
    template = pack["template"]
    theme = pack["theme"]
    tokens = theme["tokens"]
    terms = theme.get("terminology", {})
    page = next(page for page in pack["layout"]["pages"] if page.get("path") == "index.html")
    sections = "".join(_render_component(section, model, terms) for section in page["sections"])
    report = model["report"]
    freshness_class, freshness_label = _freshness(model, config)
    primary = config.get("theme", {}).get("primaryColor", tokens["primary"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'">
<meta name="description" content="{escape(report.get('subtitle', report['title']))}"><title>{escape(report['title'])} | {escape(template['displayName'])}</title><style>
:root{{--primary:{primary};--accent:{tokens['accent']};--canvas:{tokens['canvas']};--surface:{tokens['surface']};--ink:#14213a;--muted:#607086;--line:#d6e0eb}}*{{box-sizing:border-box}}body{{margin:0;background:var(--canvas);color:var(--ink);font:16px/1.5 "Segoe UI",Arial,sans-serif}}.shell{{width:min(calc(100% - 36px),1280px);margin:auto}}header{{background:linear-gradient(140deg,#07192e,#103154);color:#fff;padding:28px 0 46px}}.mast{{display:flex;justify-content:space-between;gap:20px}}.classification{{border:1px solid #ffffff55;border-radius:99px;padding:6px 10px}}h1{{font-size:clamp(2.6rem,6vw,5rem);line-height:1;margin:28px 0 12px}}.meta{{display:flex;gap:18px;flex-wrap:wrap;color:#c5d4e3}}main{{padding:24px 0 44px}}.card,.metric,.group,.notice{{background:var(--surface);border:1px solid var(--line);border-radius:17px;box-shadow:0 14px 38px #14284812}}.card{{padding:24px;margin-top:16px}}.status{{border-top:5px solid var(--accent)}}.eyebrow{{color:var(--primary);font-weight:800;text-transform:uppercase}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:-42px}}.metric{{padding:20px;border-top:4px solid var(--primary)}}.metric p,.metric span,.metric small{{display:block;color:var(--muted)}}.metric strong{{display:block;font-size:2.2rem}}.groups{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}.group{{padding:18px}}.group span{{color:var(--accent);font-weight:800}}.signals li{{margin:10px 0}}.signals span,td span{{display:block;color:var(--muted)}}table{{width:100%;border-collapse:collapse}}th,td{{padding:13px;text-align:left;border-top:1px solid var(--line);vertical-align:top}}th{{color:var(--muted);font-size:.72rem;text-transform:uppercase}}.notice{{padding:18px;margin-top:16px}}footer{{padding:22px 0;color:var(--muted)}}@media(max-width:850px){{.metrics,.groups{{grid-template-columns:repeat(2,1fr)}}}}@media(max-width:620px){{.metrics,.groups{{grid-template-columns:1fr}}table,tbody,tr,td{{display:block}}thead{{position:absolute;width:1px;height:1px;overflow:hidden}}}}@media print{{body{{background:#fff}}.card,.metric,.group{{box-shadow:none}}}}
</style></head><body data-template="{escape(template['id'])}" data-template-version="{escape(template['version'])}" data-item-count="{len(model.get('items', []))}"><header><div class="shell"><div class="mast"><strong>ReportKit · {escape(template['displayName'])}</strong><span class="classification">{escape(report['classification'])}</span></div><h1>{escape(report['title'])}</h1><p>{escape(report.get('subtitle', ''))}</p><div class="meta"><span>Period: {escape(report.get('period', {}).get('label', 'Not specified'))}</span><span>Data as of: {escape(_format_datetime(report['dataAsOf']))}</span><span>Generated: {escape(_format_datetime(report['generatedAt']))}</span><span class="freshness {freshness_class}">{escape(freshness_label)}</span></div></div></header><main class="shell">{sections}</main><footer class="shell"><span>{escape(report['id'])} · {escape(template['id'])}@{escape(template['version'])} · {escape(pack['digest'])}</span></footer></body></html>"""


def build_pack_site(
    pack_path: Path,
    model_path: Path,
    config_path: Path,
    output_path: Path,
    lock_path: Path,
    overwrite: bool = False,
) -> dict[str, Any]:
    output_path = lexical_absolute_path(output_path)
    pack_report, pack = validate_pack(pack_path)
    if pack is None:
        return pack_report
    input_errors: list[dict[str, str]] = []
    model = _load_json_for_validation(model_path, input_errors)
    config = _load_json_for_validation(config_path, input_errors)
    if input_errors or model is None or config is None:
        return validation_report(input_errors)
    model_report = validate_model(model, pack["template"])
    config_report = validate_config(config, pack["template"])
    custom_config_report = validation_report()
    if pack["configSchema"] is not None:
        custom_config_report = validation_report(validate_instance(
            config,
            pack["configSchema"],
            path="configuration",
        ))
    lock_report = validate_lock(lock_path, pack)
    input_report = merge_reports(pack_report, model_report, config_report, custom_config_report, lock_report)
    if input_report["errors"]:
        return input_report
    pages = pack["layout"]["pages"]
    if len(pages) != 1 or pages[0].get("path") != "index.html" or pages[0].get("repeatFor") is not None:
        return validation_report([message(
            "pack-renderer-scope",
            "The Hack Week declarative renderer currently supports one non-repeating index.html page.",
            "layout.json.pages",
        )])

    temporary, backup, output_report = prepare_output_paths(output_path, overwrite)
    if output_report["errors"]:
        return output_report
    assert temporary is not None and backup is not None
    temporary.mkdir(parents=True)
    (temporary / "index.html").write_text(render_pack(pack, model, config), encoding="utf-8", newline="\n")
    write_json(temporary / OUTPUT_MARKER, {
        "markerVersion": "1.0",
        "managedBy": "ReportKit",
        "reportId": model["report"]["id"],
    })
    preliminary = merge_reports(input_report)
    write_json(temporary / "validation-report.json", preliminary)
    manifest = {
        "manifestVersion": "1.0",
        "reportKitVersion": REPORTKIT_VERSION,
        "schemaVersion": model["schemaVersion"],
        "template": {
            "id": pack["template"]["id"],
            "version": pack["template"]["version"],
            "kind": "declarative",
            "source": "project",
            "digest": pack["digest"],
        },
        "reportId": model["report"]["id"],
        "generatedAt": model["report"]["generatedAt"],
        "dataAsOf": model["report"]["dataAsOf"],
        "classification": model["report"]["classification"],
        "pageCount": 1,
        "itemCount": len(model.get("items", [])),
        "files": [OUTPUT_MARKER, "index.html", "report-manifest.json", "validation-report.json"],
        "validation": {
            "status": preliminary["status"],
            "errors": preliminary["summary"]["errorCount"],
            "warnings": preliminary["summary"]["warningCount"],
            "info": preliminary["summary"]["infoCount"],
        },
    }
    try:
        manifest["reproducibility"] = make_reproducibility(model, config, temporary)
    except (OSError, ValueError) as exception:
        shutil.rmtree(temporary)
        return validation_report([message("artifact-identity", f"Cannot identify generated artifacts: {exception}", "report-manifest.json.reproducibility")])
    write_json(temporary / "report-manifest.json", manifest)
    site_report = validate_site(temporary, len(model.get("items", [])))
    final_report = merge_reports(input_report, site_report)
    manifest["validation"] = {
        "status": final_report["status"],
        "errors": final_report["summary"]["errorCount"],
        "warnings": final_report["summary"]["warningCount"],
        "info": final_report["summary"]["infoCount"],
    }
    write_json(temporary / "validation-report.json", final_report)
    try:
        manifest["reproducibility"] = make_reproducibility(model, config, temporary)
    except (OSError, ValueError) as exception:
        shutil.rmtree(temporary)
        return validation_report([message("artifact-identity", f"Cannot identify generated artifacts: {exception}", "report-manifest.json.reproducibility")])
    write_json(temporary / "report-manifest.json", manifest)
    if final_report["errors"]:
        shutil.rmtree(temporary)
        return final_report
    refreshed_report = validate_site(temporary, len(model.get("items", [])))
    if refreshed_report["errors"]:
        shutil.rmtree(temporary)
        return merge_reports(final_report, refreshed_report)
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
        try:
            manifest["reproducibility"] = make_reproducibility(model, config, output_path)
        except (OSError, ValueError) as exception:
            return validation_report([message("artifact-identity", f"Cannot identify generated artifacts: {exception}", "report-manifest.json.reproducibility")])
        write_json(output_path / "report-manifest.json", manifest)
        refreshed_report = validate_site(output_path, len(model.get("items", [])))
        if refreshed_report["errors"]:
            return merge_reports(final_report, refreshed_report)
    return final_report
