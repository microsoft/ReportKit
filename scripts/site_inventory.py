"""Fail-closed, metadata-only inventory of a generated static site."""

from __future__ import annotations

import os
import stat
from pathlib import Path


ALLOWED_SITE_SUFFIXES = frozenset({
    ".html", ".htm", ".css", ".svg", ".json",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico",
})
_WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$",
    *(f"COM{number}" for number in "123456789¹²³"),
    *(f"LPT{number}" for number in "123456789¹²³"),
}


def _safe_component(name: str) -> bool:
    return (
        bool(name)
        and name not in {".", ".."}
        and name == name.rstrip(" .")
        and not any(ord(character) < 32 or character in '<>:"/\\|?*' for character in name)
        and name.split(".", 1)[0].upper() not in _WINDOWS_RESERVED_NAMES
    )


def inspect_site_inventory(site: Path) -> tuple[list[Path], list[dict[str, str]]]:
    """List regular files and errors without opening file contents or following links.

    Paths retain the supplied root; diagnostics use root-relative POSIX paths.
    Any error invalidates the entire inventory, including otherwise regular files
    with unsupported suffixes. Callers must reject redirected root ancestors first.
    This is not an atomic snapshot: concurrent changes between lstat, scandir and
    subsequent caller reads require external isolation, not this path-based check.
    """
    files: list[Path] = []
    errors: list[dict[str, str]] = []

    def error(code: str, text: str, relative: str) -> None:
        errors.append({"code": code, "message": text, "path": relative})

    for component in site.parts:
        if component not in {site.anchor, ".", ".."} and not _safe_component(component):
            error("site-path-alias", "Site path contains an unsafe or Windows-aliased name.", ".")
            return files, errors

    pending = [(site, ".")]
    while pending:
        path, relative = pending.pop()
        try:
            status = path.lstat()
        except (OSError, ValueError):
            error("site-inventory-io", "Cannot inspect filesystem entry.", relative)
            continue

        attributes = getattr(status, "st_file_attributes", 0)
        if stat.S_ISLNK(status.st_mode) or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            error("site-link-redirection", "Site entries cannot be symbolic links, junctions, or reparse points.", relative)
            continue
        if relative != "." and not _safe_component(path.name):
            error("site-path-alias", "Site entry has an unsafe or Windows-aliased name.", relative)
            continue
        if stat.S_ISDIR(status.st_mode):
            try:
                with os.scandir(path) as entries:
                    children = sorted((entry.name for entry in entries), reverse=True)
            except (OSError, ValueError):
                error("site-inventory-io", "Cannot enumerate directory.", relative)
                continue
            for name in children:
                child_relative = name if relative == "." else f"{relative}/{name}"
                pending.append((path / name, child_relative))
        elif relative == ".":
            error("site-root-type", "Site root must be a regular directory.", relative)
        elif not stat.S_ISREG(status.st_mode):
            error("site-entry-type", "Site entries must be regular files or directories.", relative)
        else:
            files.append(path)
            if path.suffix.lower() not in ALLOWED_SITE_SUFFIXES:
                error("site-file-type", "File extension is not allowed in a generated static site.", relative)

    files.sort(key=lambda path: path.relative_to(site).as_posix())
    errors.sort(key=lambda issue: (issue["path"], issue["code"], issue["message"]))
    return files, errors
