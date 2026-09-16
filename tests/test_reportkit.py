"""Executable ReportKit v1 engine tests."""

from __future__ import annotations

import hashlib
import json
import re
import struct
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from reportkit_engine import load_json, validate_model, validate_site  # noqa: E402


class ReportKitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, "-B", str(SCRIPTS / "create_sample.py")], check=True)
        cls.example = ROOT / "examples" / "operational-snapshot"
        cls.model_path = cls.example / "canonical-report.json"
        cls.config_path = cls.example / "executive-health.config.json"
        cls.capability_path = ROOT / "templates" / "executive-health" / "template.json"

    def build(self, output: Path) -> None:
        subprocess.run([
            sys.executable, "-B", str(SCRIPTS / "build"),
            "--template", "executive-health",
            "--data", str(self.model_path),
            "--config", str(self.config_path),
            "--output", str(output),
        ], check=True)

    def test_sample_has_401_records_and_valid_counts(self) -> None:
        model = load_json(self.model_path)
        self.assertEqual(401, len(model["items"]))
        statuses = {}
        for item in model["items"]:
            statuses[item["status"]] = statuses.get(item["status"], 0) + 1
        self.assertEqual({"healthy": 352, "warning": 37, "critical": 12}, statuses)
        report = validate_model(model, load_json(self.capability_path))
        self.assertEqual("passed", report["status"], report)

    def test_deterministic_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            first = Path(temp) / "first"
            second = Path(temp) / "second"
            self.build(first)
            self.build(second)
            first_hashes = {
                file.relative_to(first).as_posix(): hashlib.sha256(file.read_bytes()).hexdigest()
                for file in sorted(first.rglob("*")) if file.is_file()
            }
            second_hashes = {
                file.relative_to(second).as_posix(): hashlib.sha256(file.read_bytes()).hexdigest()
                for file in sorted(second.rglob("*")) if file.is_file()
            }
            self.assertEqual(first_hashes, second_hashes)

    def test_html_is_escaped_and_script_free(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "site"
            self.build(output)
            html = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn("&lt;unsafe-test&gt;", html)
            self.assertNotIn("<unsafe-test>", html)
            self.assertNotIn("<script", html.lower())

    def test_site_links_counts_and_accessibility(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "site"
            self.build(output)
            report = validate_site(output, expected_item_count=401)
            self.assertEqual("passed", report["status"], report)
            manifest = json.loads((output / "report-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(401, manifest["itemCount"])
            html = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn("<main", html)
            self.assertIn("<h1", html)
            self.assertIn("classification", html)
            self.assertIn("freshness", html)

    def test_sensitive_field_is_rejected(self) -> None:
        model = load_json(self.model_path)
        model["provenance"]["accessToken"] = "not-a-real-token"
        report = validate_model(model, load_json(self.capability_path))
        self.assertEqual("failed", report["status"])
        self.assertIn("sensitive-field", {item["code"] for item in report["errors"]})

    def test_machine_contracts_are_parseable_and_aligned(self) -> None:
        schemas = list((ROOT / "schema").glob("*.json"))
        self.assertEqual(8, len(schemas))
        for schema_path in schemas:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            self.assertEqual("https://json-schema.org/draft/2020-12/schema", schema["$schema"])
        for capability_path in (ROOT / "templates").glob("*/template.json"):
            capability = json.loads(capability_path.read_text(encoding="utf-8"))
            self.assertEqual("1.0", capability["contractVersion"])
            self.assertIn("1.0", capability["supportedSchemaVersions"])
            self.assertTrue(capability["primaryDecision"])
        portfolio = json.loads(
            (ROOT / "templates" / "portfolio-team" / "template.json").read_text(encoding="utf-8")
        )
        self.assertIn("groups[].label", portfolio["requiredFields"])
        self.assertNotIn("groups[].name", portfolio["requiredFields"])

    def test_all_prototype_html_links_resolve(self) -> None:
        failures = []
        for prototype in (ROOT / "templates").glob("*/prototype.html"):
            text = prototype.read_text(encoding="utf-8")
            for link in sorted(set(re.findall(r'href="([^"]+\.html)"', text))):
                if not (prototype.parent / link).is_file():
                    failures.append(f"{prototype.parent.name}: {link}")
        self.assertEqual([], failures)

    def test_repository_has_no_package_or_local_environment_artifacts(self) -> None:
        prohibited = [
            ROOT / "pyproject.toml",
            ROOT / ".git",
            ROOT / ".venv",
            ROOT / "reportkit.egg-info",
        ]
        self.assertFalse(any(path.exists() for path in prohibited), prohibited)
        self.assertEqual([], list(ROOT.rglob("__pycache__")))

    def test_required_marketing_screenshots_exist_with_expected_dimensions(self) -> None:
        contract = json.loads(
            (ROOT / "tests" / "visual" / "screenshot-contract.json").read_text(encoding="utf-8")
        )
        self.assertEqual(19, len(contract["captures"]))
        screenshot_root = ROOT / "docs" / "assets" / "screenshots"
        for capture in contract["captures"]:
            image = screenshot_root / capture["name"]
            self.assertTrue(image.is_file(), capture["name"])
            with image.open("rb") as stream:
                self.assertEqual(b"\x89PNG\r\n\x1a\n", stream.read(8))
                length = struct.unpack(">I", stream.read(4))[0]
                self.assertEqual(b"IHDR", stream.read(4))
                width, height = struct.unpack(">II", stream.read(8))
                stream.seek(length - 8, 1)
            self.assertEqual(capture["width"], width, capture["name"])
            if not capture["fullPage"]:
                self.assertEqual(capture["height"], height, capture["name"])
            else:
                self.assertGreaterEqual(height, capture["height"], capture["name"])

    def test_marketing_pages_are_public_safe_and_have_required_metadata(self) -> None:
        prohibited = re.compile(
            r"S360|Azure DevOps|\bADO\b|microsoft\.com|tenant[-_ ]?id|"
            r"Classification Internal|Template preview",
            re.IGNORECASE,
        )
        pages = [
            ROOT / "templates" / "executive-health" / "prototype.html",
            ROOT / "templates" / "action-risk" / "action-risk.html",
            ROOT / "templates" / "portfolio-team" / "portfolio-team.html",
            ROOT / "templates" / "operational-health" / "operational-health.html",
            ROOT / "templates" / "compliance-readiness" / "compliance-readiness.html",
        ]
        for page in pages:
            text = page.read_text(encoding="utf-8")
            self.assertIsNone(prohibited.search(text), page)
            self.assertIn("Public sample", text, page)
            self.assertRegex(text, r"Data as of", page)
            self.assertRegex(text, r"Generated", page)
            self.assertRegex(text, r"Fresh|Current", page)

    def test_failed_build_preserves_previous_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "site"
            self.build(output)
            before = (output / "index.html").read_bytes()
            broken = Path(temp) / "broken.json"
            model = load_json(self.model_path)
            model["report"].pop("generatedAt")
            broken.write_text(json.dumps(model), encoding="utf-8")
            result = subprocess.run([
                sys.executable, "-B", str(SCRIPTS / "build"),
                "--template", "executive-health",
                "--data", str(broken),
                "--config", str(self.config_path),
                "--output", str(output),
            ], check=False)
            self.assertNotEqual(0, result.returncode)
            self.assertEqual(before, (output / "index.html").read_bytes())

    @classmethod
    def tearDownClass(cls) -> None:
        cache = SCRIPTS / "__pycache__"
        if cache.exists():
            shutil.rmtree(cache)


if __name__ == "__main__":
    unittest.main()
