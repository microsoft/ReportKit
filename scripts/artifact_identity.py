"""Deterministic content identities, not signatures or provenance attestations."""

from __future__ import annotations

import hashlib
import json
import stat
from pathlib import Path
from typing import Any

from json_schema import validate_instance
from site_inventory import ALLOWED_SITE_SUFFIXES, _safe_component, inspect_site_inventory, relative_site_path

ROOT = Path(__file__).resolve().parents[1]
_MANIFEST = "report-manifest.json"
_RENDERER_SOURCES = (
    "artifact_identity.py", "builtin_renderers.py", "json_schema.py",
    "reportkit_engine.py", "site_inventory.py", "template_pack.py",
)


def canonical_digest(value: Any) -> str:
    """Hash sorted, compact, UTF-8 JSON; non-finite numbers are not JSON."""
    content = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def renderer_identity() -> dict[str, str]:
    """Identify normalized renderer/schema source bytes without Git or timestamps."""
    paths = [ROOT / "scripts" / name for name in _RENDERER_SOURCES]
    paths.extend((ROOT / "schema").glob("*.json"))
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda value: value.relative_to(ROOT).as_posix()):
        content = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8") + b"\0")
        digest.update(content + b"\0")
    return {"id": "reportkit-python", "digest": "sha256:" + digest.hexdigest()}


def validate_capabilities(template: dict[str, Any]) -> list[dict[str, str]]:
    """Validate designed/runtime records and the legacy runtime alias."""
    from reportkit_engine import load_json

    errors = validate_instance(
        template, load_json(ROOT / "schema" / "template-capability-v1.schema.json"), path="template.json",
    )
    if (
        "features" in template and "implementationCapabilities" in template
        and template["features"] != template["implementationCapabilities"]
    ):
        errors.append({
            "code": "capability-alias-mismatch",
            "message": "features must equal implementationCapabilities; designCapabilities is not a runtime promise.",
            "path": "template.json.features",
        })
    return errors


def _source_identifiers(model: dict[str, Any]) -> list[str]:
    provenance = model["provenance"]
    adapter = provenance["adapter"]
    identifiers = {f"adapter:{adapter['id']}@{adapter['version']}"}
    identifiers.update(f"source:{source['type']}:{source['name']}" for source in provenance["sources"])
    return sorted(identifiers)


def _artifact_digest(path: Path) -> str:
    status = path.lstat()
    if not stat.S_ISREG(status.st_mode) or getattr(status, "st_file_attributes", 0) & 0x400:
        raise ValueError("Artifact is not a regular, non-redirected file.")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _inventory_paths(site: Path, files: list[Path]) -> dict[str, Path]:
    paths = {}
    for path in files:
        relative = Path(relative_site_path(site, path))
        if (
            not relative.parts
            or not all(_safe_component(component) for component in relative.parts)
            or path.suffix.lower() not in ALLOWED_SITE_SUFFIXES
        ):
            raise ValueError("Artifact paths must come from a validated site inventory.")
        name = relative.as_posix()
        if name in paths:
            raise ValueError("Artifact inventory contains duplicate paths.")
        paths[name] = path
    return paths


def make_reproducibility(model: dict[str, Any], config: dict[str, Any], site: Path) -> dict[str, Any]:
    """Describe validated inputs and regular output bytes in an owned build directory.

    Before the first manifest write, its future file list is the complete inventory
    plus report-manifest.json. Once present, its listed files must match inventory.
    Refresh this record whenever validation-report.json changes. The manifest is
    deliberately never hashed, avoiding self-reference.
    """
    from reportkit_engine import load_json

    files, errors = inspect_site_inventory(site)
    if errors:
        raise ValueError("Cannot identify a site with filesystem inventory errors.")
    paths = _inventory_paths(site, files)
    if _MANIFEST in paths:
        manifest = load_json(paths[_MANIFEST])
        declared = manifest.get("files")
        if (
            not isinstance(declared, list) or any(not isinstance(name, str) for name in declared)
            or len(declared) != len(set(declared)) or set(declared) != set(paths)
        ):
            raise ValueError("Manifest files must exactly match the validated inventory.")
    return {
        "canonicalModelDigest": canonical_digest(model),
        "configurationDigest": canonical_digest(config),
        "renderer": renderer_identity(),
        "sourceIdentifiers": _source_identifiers(model),
        "artifactHashes": {name: _artifact_digest(paths[name]) for name in sorted(paths) if name != _MANIFEST},
    }


def verify_identity(manifest: dict[str, Any], site: Path, files: list[Path]) -> list[dict[str, str]]:
    """Verify shape and artifact bytes using only an already validated inventory.

    Model/configuration/source identities are reported claims: original inputs and
    renderer sources need not be available with a standalone site. File lstat/open
    remains subject to concurrent mutation; callers must isolate untrusted writes.
    """
    from reportkit_engine import load_json

    schema = load_json(ROOT / "schema" / "report-manifest-v1.schema.json")
    identity_schema = {**schema["properties"]["reproducibility"], "$defs": schema["$defs"]}
    identity = manifest.get("reproducibility")
    errors = validate_instance(identity, identity_schema, path="report-manifest.json.reproducibility")
    if errors:
        return errors
    assert isinstance(identity, dict)

    def error(code: str, text: str, path: str) -> None:
        errors.append({"code": code, "message": text, "path": path})

    sources = identity["sourceIdentifiers"]
    if sources != sorted(sources):
        error("identity-source-order", "Source identifiers must be sorted.", "report-manifest.json.reproducibility.sourceIdentifiers")
    try:
        paths = _inventory_paths(site, files)
    except ValueError:
        error("identity-inventory", "Artifact verification requires a contained, allowlisted inventory.", ".")
        return errors
    declared = manifest.get("files")
    if (
        not isinstance(declared, list) or any(not isinstance(name, str) for name in declared)
        or len(declared) != len(set(declared)) or set(declared) != set(paths)
    ):
        error("identity-file-set", "Manifest files must exactly match the validated inventory.", "report-manifest.json.files")
        return errors
    expected = set(paths) - {_MANIFEST}
    hashes = identity["artifactHashes"]
    if set(hashes) != expected:
        error("identity-artifact-set", "Artifact hashes must cover every listed file except report-manifest.json.", "report-manifest.json.reproducibility.artifactHashes")
        return errors
    for name in sorted(expected):
        try:
            actual = _artifact_digest(paths[name])
        except (OSError, ValueError):
            error("identity-artifact-read", "Cannot hash a regular artifact file.", name)
            continue
        if actual != hashes[name]:
            error("identity-artifact-mismatch", "Artifact bytes differ from their recorded SHA-256 digest.", name)
    return sorted(errors, key=lambda issue: (issue["path"], issue["code"]))
