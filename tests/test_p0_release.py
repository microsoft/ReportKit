"""Automated P0 release gates for the ReportKit marketing preview."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]


class ReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.references: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        element_id = attributes.get("id")
        if element_id:
            self.ids.add(element_id)
        for attribute in ("href", "src"):
            value = attributes.get(attribute)
            if value:
                self.references.append((attribute, value))


def parse_html(path: Path) -> ReferenceParser:
    parser = ReferenceParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def report_html_files(root: Path = ROOT) -> list[Path]:
    files = list((root / "templates").rglob("*.html"))
    files.extend((root / "examples").rglob("*.html"))
    files.extend((root / "showcase").rglob("*.html"))
    return sorted(files)


class P0ReleaseTests(unittest.TestCase):
    def test_clean_copy_readme_workflow_is_offline_and_portable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            checkout = Path(temp) / "ReportKit clean checkout"
            shutil.copytree(
                ROOT,
                checkout,
                ignore=shutil.ignore_patterns(
                    ".git", ".venv", "node_modules", "__pycache__", "*.pyc", "*.pyo"
                ),
            )
            blocker = Path(temp) / "network-blocker"
            blocker.mkdir()
            (blocker / "sitecustomize.py").write_text(
                "import socket\n"
                "def blocked(*args, **kwargs):\n"
                "    raise RuntimeError('Network access is disabled by the P0 smoke test')\n"
                "socket.create_connection = blocked\n"
                "socket.getaddrinfo = blocked\n",
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            environment["PYTHONPATH"] = str(blocker)
            commands = [
                [
                    sys.executable,
                    "-B",
                    "scripts/validate",
                    "examples/operational-snapshot/canonical-report.json",
                    "--kind",
                    "model",
                    "--template",
                    "executive-health",
                ],
                [
                    sys.executable,
                    "-B",
                    "scripts/build",
                    "--template",
                    "executive-health",
                    "--data",
                    "examples/operational-snapshot/canonical-report.json",
                    "--config",
                    "examples/operational-snapshot/executive-health.config.json",
                    "--output",
                    "report-site",
                ],
                [
                    sys.executable,
                    "-B",
                    "scripts/validate",
                    "report-site",
                    "--kind",
                    "site",
                ],
            ]
            for command in commands:
                subprocess.run(command, cwd=checkout, env=environment, check=True)

            generated = checkout / "report-site"
            self.assertTrue((generated / "index.html").is_file())
            forbidden_paths = (str(ROOT), str(checkout), str(Path.home()))
            for output in generated.rglob("*"):
                if not output.is_file() or output.suffix not in {".html", ".json"}:
                    continue
                text = output.read_text(encoding="utf-8")
                for forbidden in forbidden_paths:
                    self.assertNotIn(forbidden, text, output)
                    self.assertNotIn(forbidden.replace("\\", "/"), text, output)
                self.assertNotRegex(text, r"(?i)\bhttps?://")

    def test_public_launch_assets_are_synthetic_and_safe(self) -> None:
        text_files = list((ROOT / "examples").rglob("*.json"))
        text_files.extend((ROOT / "examples").rglob("*.html"))
        text_files.extend((ROOT / "templates").rglob("*.html"))
        text_files.extend((ROOT / "showcase").rglob("*.html"))
        text_files.append(ROOT / "docs" / "assets" / "reportkit-architecture.svg")
        prohibited = [
            re.compile(r"(?i)\b(access[_-]?token|client[_-]?secret|password|connection string)\b"),
            re.compile(r"(?i)-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
            re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b"),
            re.compile(r"(?i)\b(?:tenant|subscription|resource)[-_ ]?id\b"),
            re.compile(r"(?i)\bClassification\s*:?\s*(?:Internal|Confidential|Restricted)\b"),
            re.compile(r"(?i)\b(?:dev\.azure\.com|microsoft\.com|windows\.net)\b"),
            re.compile(r"(?i)\b[A-Z]:[\\/]Users[\\/]"),
        ]
        failures = []
        for path in text_files:
            text = path.read_text(encoding="utf-8")
            for expression in prohibited:
                if expression.search(text):
                    failures.append(f"{path.relative_to(ROOT)}: {expression.pattern}")
        for image in (ROOT / "docs" / "assets" / "screenshots").rglob("*.png"):
            raw = image.read_bytes().lower()
            for marker in (b"microsoft.com", b"dev.azure.com", b"access_token", b"password"):
                if marker in raw:
                    failures.append(f"{image.relative_to(ROOT)}: {marker.decode()}")
        self.assertEqual([], failures)

        report_pages = list((ROOT / "templates").rglob("*.html"))
        report_pages.append(
            ROOT
            / "examples"
            / "operational-snapshot"
            / "generated"
            / "executive-health"
            / "index.html"
        )
        for page in report_pages:
            self.assertIn("Public sample", page.read_text(encoding="utf-8"), page)

    def test_every_local_html_reference_and_fragment_resolves(self) -> None:
        parsers = {path.resolve(): parse_html(path) for path in report_html_files()}
        failures = []
        for page, parser in parsers.items():
            for attribute, reference in parser.references:
                parsed = urlsplit(reference)
                if parsed.scheme == "data" and reference.lower().startswith("data:image/"):
                    continue
                if parsed.scheme or parsed.netloc:
                    failures.append(f"{page.relative_to(ROOT)}: external {attribute}={reference}")
                    continue
                target_path = unquote(parsed.path)
                target = (page.parent / target_path).resolve() if target_path else page
                try:
                    target.relative_to(ROOT.resolve())
                except ValueError:
                    failures.append(f"{page.relative_to(ROOT)}: path escape {reference}")
                    continue
                if not target.exists():
                    failures.append(f"{page.relative_to(ROOT)}: missing {reference}")
                    continue
                if parsed.fragment and target.suffix.lower() == ".html":
                    target_parser = parsers.get(target) or parse_html(target)
                    if unquote(parsed.fragment) not in target_parser.ids:
                        failures.append(f"{page.relative_to(ROOT)}: missing fragment {reference}")
        self.assertEqual([], failures)

    def test_screenshot_contract_covers_p0_desktop_and_mobile_requirements(self) -> None:
        contract = json.loads(
            (ROOT / "tests" / "visual" / "screenshot-contract.json").read_text(encoding="utf-8")
        )
        captures = {capture["name"]: capture for capture in contract["captures"]}
        templates = [
            "executive-health",
            "action-risk",
            "portfolio-team",
            "operational-health",
            "compliance-readiness",
        ]
        for template in templates:
            hero = captures[f"{template}-hero.png"]
            mobile = captures[f"mobile/{template}-mobile.png"]
            self.assertEqual((1440, 1000, False), (hero["width"], hero["height"], hero["fullPage"]))
            self.assertEqual((390, 844, False), (mobile["width"], mobile["height"], mobile["fullPage"]))
            source = (ROOT / hero["page"]).read_text(encoding="utf-8")
            self.assertIn("Public sample", source)
            self.assertRegex(source, r"Data as of")
            self.assertRegex(source, r"Generated")
            self.assertRegex(source, r"Fresh|Current")
            self.assertNotRegex(source, r"(?i)Template preview")

        capture_script = (ROOT / "scripts" / "capture-screenshots.mjs").read_text(encoding="utf-8")
        self.assertIn("Horizontal overflow detected", capture_script)
        self.assertIn('colorScheme: contract.defaults.colorScheme', capture_script)
        self.assertIn('deviceScaleFactor: contract.defaults.deviceScaleFactor', capture_script)
        self.assertIn('reducedMotion: contract.defaults.reducedMotion', capture_script)

    def test_marketing_claims_match_current_implementation(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        showcase = (ROOT / "showcase" / "index.html").read_text(encoding="utf-8")
        self.assertIn("all five built-in", readme)
        self.assertNotIn("| Other four renderers | Not implemented yet |", readme)
        self.assertIn("not production certification", readme)
        self.assertIn("not a hosted service", readme)
        self.assertIn("not a package that users must deploy", readme)
        self.assertEqual(5, showcase.count("Generated · Experimental"))
        self.assertIn("Experimental local showcase", showcase)
        for template in ("executive-health", "action-risk", "portfolio-team", "operational-health", "compliance-readiness"):
            self.assertIn(f"generated/{template}/index.html", showcase)
            self.assertIn(f"generated/{template}/index.html", readme)
            generated = ROOT / "examples" / "operational-snapshot" / "generated" / template
            self.assertEqual(template, json.loads((generated / "report-manifest.json").read_text(encoding="utf-8"))["template"]["id"])
        for template in ("action-risk", "portfolio-team", "operational-health", "compliance-readiness"):
            prototype = (ROOT / "templates" / template / "prototype.html").read_text(encoding="utf-8")
            self.assertIn("Archived hand-authored design prototype", prototype)
            self.assertIn("not generated from canonical data", prototype)


if __name__ == "__main__":
    unittest.main()
