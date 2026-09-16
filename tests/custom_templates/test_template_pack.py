"""Contract, security, digest, and rendering tests for declarative template packs."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from reportkit_engine import load_json, validate_site  # noqa: E402
from template_pack import build_pack_site, pack_digest, validate_lock, validate_pack  # noqa: E402


class DeclarativeTemplatePackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project = ROOT / "examples" / "custom-template-project"
        cls.pack = cls.project / "templates" / "contoso-release-review"
        cls.model = cls.pack / "examples" / "canonical-report.json"
        cls.config = cls.pack / "examples" / "configuration.json"

    def test_valid_folder_and_zip_have_same_identity(self) -> None:
        folder_report, folder_pack = validate_pack(self.pack)
        self.assertEqual("passed", folder_report["status"], folder_report)
        self.assertIsNotNone(folder_pack)
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "release-review.zip"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
                for file in sorted(self.pack.rglob("*")):
                    if file.is_file():
                        output.write(file, Path(self.pack.name) / file.relative_to(self.pack))
            zip_report, zip_pack = validate_pack(archive)
            self.assertEqual("passed", zip_report["status"], zip_report)
            self.assertEqual(folder_pack["digest"], zip_pack["digest"])

    def test_declarative_build_is_deterministic_and_records_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            first = Path(temp) / "first"
            second = Path(temp) / "second"
            lock = self.project / "reportkit.lock.json"
            first_report = build_pack_site(self.pack, self.model, self.config, first, lock)
            second_report = build_pack_site(self.pack, self.model, self.config, second, lock)
            self.assertFalse(first_report["errors"], first_report)
            self.assertEqual(first_report, second_report)
            hashes = lambda folder: {
                path.relative_to(folder).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in folder.rglob("*") if path.is_file()
            }
            self.assertEqual(hashes(first), hashes(second))
            manifest = load_json(first / "report-manifest.json")
            _, validated_pack = validate_pack(self.pack)
            self.assertEqual("declarative", manifest["template"]["kind"])
            self.assertEqual("project", manifest["template"]["source"])
            self.assertEqual(validated_pack["digest"], manifest["template"]["digest"])
            self.assertEqual("passed-with-warnings", validate_site(first, 2)["status"])
            self.assertEqual(
                "passed-with-warnings",
                load_json(first / "validation-report.json")["status"],
            )

    def test_pack_digest_changes_when_bytes_change(self) -> None:
        report, pack = validate_pack(self.pack)
        self.assertFalse(report["errors"], report)
        changed = dict(pack["files"])
        changed["README.md"] += b"\nChanged bytes.\n"
        self.assertNotEqual(pack["digest"], pack_digest(changed))

    def test_pack_digest_normalizes_text_line_endings(self) -> None:
        report, pack = validate_pack(self.pack)
        self.assertFalse(report["errors"], report)
        crlf = {
            name: (
                content.replace(b"\r\n", b"\n").replace(b"\r", b"\n").replace(b"\n", b"\r\n")
                if Path(name).suffix.lower() in {".json", ".md", ".txt"} or not Path(name).suffix
                else content
            )
            for name, content in pack["files"].items()
        }
        self.assertEqual(pack["digest"], pack_digest(crlf))

    def test_unknown_component_and_css_token_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            copied = Path(temp) / "pack"
            shutil.copytree(self.pack, copied)
            layout_path = copied / "layout.json"
            layout = load_json(layout_path)
            layout["pages"][0]["sections"][0]["component"] = "arbitrary-html"
            layout_path.write_text(json.dumps(layout), encoding="utf-8")
            theme_path = copied / "theme.json"
            theme = load_json(theme_path)
            theme["tokens"]["primary"] = "#fff;}</style><script>"
            theme["name"] = "x" * 81
            theme_path.write_text(json.dumps(theme), encoding="utf-8")
            report, _ = validate_pack(copied)
            codes = {issue["code"] for issue in report["errors"]}
            self.assertIn("pack-component", codes)
            self.assertIn("pack-theme-color", codes)
            self.assertIn("json-schema-max-length", codes)

    def test_zip_traversal_symlink_and_active_files_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "malicious.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("../outside.txt", "escape")
                output.writestr("template/script.js", "alert(1)")
                output.writestr("template/nested.zip", b"PK\x03\x04")
                link = zipfile.ZipInfo("template/link")
                link.create_system = 3
                link.external_attr = (stat.S_IFLNK | 0o777) << 16
                output.writestr(link, "target")
            report, _ = validate_pack(archive)
            codes = {issue["code"] for issue in report["errors"]}
            self.assertTrue({"pack-path", "pack-file-type", "pack-symlink"}.issubset(codes), report)

    def test_project_state_and_lock_are_non_secret_and_digest_bound(self) -> None:
        project = load_json(self.project / "reportkit.project.json")
        lock = load_json(self.project / "reportkit.lock.json")
        report, pack = validate_pack(self.pack)
        self.assertFalse(report["errors"], report)
        self.assertEqual(pack["digest"], project["template"]["digest"])
        self.assertEqual(pack["digest"], lock["templates"][0]["digest"])
        serialized = json.dumps({"project": project, "lock": lock})
        self.assertNotRegex(serialized, r"(?i)(password|access.?token|authorization|private.?key)")
        self.assertNotRegex(serialized, r"[A-Za-z]:[\\/]")
        self.assertEqual("build-review", project["currentPhase"])
        with tempfile.TemporaryDirectory() as temp:
            stale_lock = copy.deepcopy(lock)
            stale_lock["templates"][0]["digest"] = "sha256:" + ("0" * 64)
            stale_path = Path(temp) / "reportkit.lock.json"
            stale_path.write_text(json.dumps(stale_lock), encoding="utf-8")
            lock_report = validate_lock(stale_path, pack)
            self.assertIn("template-lock-digest", {issue["code"] for issue in lock_report["errors"]})

    def test_skill_exposes_the_four_guided_phases(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        phases = [
            "## Phase 1 — Choose a template",
            "## Phase 2 — Add your data",
            "## Phase 3 — Build and review",
            "## Phase 4 — Return files or export manually",
        ]
        positions = [skill.index(phase) for phase in phases]
        self.assertEqual(sorted(positions), positions)
        self.assertIn("The destination determines where the generated report lives.", skill)
        self.assertNotIn("push to your source", skill.lower())

    def test_skill_onboarding_and_ui_metadata_are_complete(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        start = skill.index("## Start here")
        guided = skill.index("## Guided path")
        onboarding = skill[start:guided]
        expected_choices = [
            "Start a new report",
            "Inspect an existing ReportKit project and continue manually",
            "Validate a custom template",
        ]
        self.assertTrue(all(choice in onboarding for choice in expected_choices))
        self.assertIn("Stop after the menu and wait.", onboarding)
        self.assertIn(
            "`1 Choose template → 2 Add data → 3 Build and review → 4 Return files or export manually`",
            skill,
        )
        self.assertIn("--lock <reportkit.lock.json>", skill)

        metadata = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn('display_name: "ReportKit"', metadata)
        self.assertIn('short_description: "Build validated static reports from operational data"', metadata)
        self.assertIn(
            'default_prompt: "Use $reportkit. Show exactly three choices: Start a new report; '
            'Inspect an existing ReportKit project and continue manually; Validate a custom template. '
            'Stop and wait for my selection."',
            metadata,
        )

    def test_declared_cases_execute_and_selection_changes_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            copied = Path(temp) / "pack"
            shutil.copytree(self.pack, copied)
            cases_path = copied / "tests" / "cases.json"
            cases = load_json(cases_path)
            cases["cases"][0]["expected"] = "failed"
            cases_path.write_text(json.dumps(cases), encoding="utf-8")
            report, _ = validate_pack(copied)
            self.assertIn("pack-case-result", {issue["code"] for issue in report["errors"]})

        with tempfile.TemporaryDirectory() as temp:
            copied = Path(temp) / "pack"
            shutil.copytree(self.pack, copied)
            layout_path = copied / "layout.json"
            layout = load_json(layout_path)
            attention = next(
                section for section in layout["pages"][0]["sections"]
                if section["component"] == "attention-table"
            )
            attention["selection"] = "blocked"
            layout_path.write_text(json.dumps(layout), encoding="utf-8")
            report, changed_pack = validate_pack(copied)
            self.assertFalse(report["errors"], report)
            html = __import__("template_pack").render_pack(
                changed_pack,
                load_json(self.model),
                load_json(self.config),
            )
            self.assertIn("Confirm reserved rollback capacity", html)
            self.assertNotIn("Name the production approval owner", html)

    def test_user_configuration_uses_custom_schema_during_build(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            invalid = load_json(self.config)
            invalid["theme"]["name"] = ""
            invalid_path = Path(temp) / "configuration.json"
            invalid_path.write_text(json.dumps(invalid), encoding="utf-8")
            report = build_pack_site(
                self.pack,
                self.model,
                invalid_path,
                Path(temp) / "site",
                self.project / "reportkit.lock.json",
            )
            self.assertEqual("failed", report["status"])
            self.assertIn("json-schema-min-length", {issue["code"] for issue in report["errors"]})

    def test_invalid_and_recursive_custom_schemas_fail_without_crashing(self) -> None:
        cases = [
            {"type": "string", "pattern": "("},
            {"$defs": {"loop": {"$ref": "#/$defs/loop"}}, "$ref": "#/$defs/loop"},
            {"type": "object", "patternProperties": {".*": {"type": "string"}}},
        ]
        for schema in cases:
            with self.subTest(schema=schema), tempfile.TemporaryDirectory() as temp:
                copied = Path(temp) / "pack"
                shutil.copytree(self.pack, copied)
                (copied / "config.schema.json").write_text(json.dumps(schema), encoding="utf-8")
                report, pack = validate_pack(copied)
                self.assertIsNone(pack)
                self.assertEqual("failed", report["status"])
                self.assertTrue(
                    any(issue["code"].startswith("pack-custom-json-schema-") for issue in report["errors"]),
                    report,
                )


if __name__ == "__main__":
    unittest.main()
