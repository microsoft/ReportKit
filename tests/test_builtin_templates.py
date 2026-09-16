"""End-to-end generated-site contracts for every built-in template."""

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from reportkit_engine import BUILTIN_TEMPLATE_IDS, build_site, load_json, validate_model, validate_site


class Records(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.items = []
        self.groups = {}
        self.body = {}
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "data-item-id" in attrs:
            self.items.append(attrs["data-item-id"])
        if "data-group-id" in attrs and "href" in attrs:
            self.groups[attrs["data-group-id"]] = attrs["href"]
        if tag == "body":
            self.body = attrs


class BuiltinTemplateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.model = {
            "schemaVersion": "1.0",
            "report": {
                "id": "fixture-report", "title": "Fixture Health", "status": "unknown",
                "classification": "Public sample", "generatedAt": "2026-09-15T18:00:00Z",
                "dataAsOf": "2026-09-15T17:00:00Z",
            },
            "metrics": [{"id": "source-total", "label": "Source supplied", "value": 9, "unit": "builds"}],
            "items": [
                {"id": "a", "title": "A issue", "status": "critical", "priority": "high", "dueDate": "2026-09-14", "blocker": "Awaiting evidence", "groupIds": ["root"], "nextAction": "Source action"},
                {"id": "b", "title": "B issue", "status": "warning", "dueDate": "2026-09-15", "groupIds": ["child"]},
                {"id": "c", "title": "C review", "status": "pending-review", "dueDate": "2026-09-22"},
                {"id": "d", "title": "D healthy", "status": "healthy", "dueDate": "2026-09-14"},
                {"id": "e", "title": "E passed", "status": "passed", "dueDate": "2026-09-14"},
                {"id": "f", "title": "F not applicable", "status": "not-applicable", "dueDate": "2026-09-14"},
                {"id": "g", "title": "G failed", "status": "failed", "dueDate": "2026-09-23"},
                {"id": "h", "title": "H blocked", "status": "blocked"},
                {"id": "j", "title": "J in progress", "status": "in-progress", "dueDate": "2026-09-16"},
            ],
            "groups": [
                {"id": "root", "label": "Parent group", "childGroupIds": ["child"], "itemIds": ["a"]},
                {"id": "child", "label": "Child group", "itemIds": ["b"]},
                {"id": "empty", "label": "Empty group"},
            ],
            "trends": [{"id": "actual-trend", "label": "Actual observations", "unit": "percent",
                        "observations": [{"date": "2026-09-14", "value": 0}, {"date": "2026-09-15", "value": 0}]}],
            "provenance": {"adapter": {"id": "fixture", "version": "1.0"},
                           "sources": [{"type": "fixture", "name": "Fixture records", "recordCount": 9}],
                           "recordCounts": {"raw": 9}},
        }

    def build(self, template, model=None, label="site"):
        model = model if model is not None else self.model
        model_path = self.root / f"{template}-{label}.json"
        config_path = self.root / f"{template}-{label}-config.json"
        model_path.write_text(json.dumps(model), encoding="utf-8")
        config_path.write_text(json.dumps({"version": "1.0", "template": {"id": template, "version": "1.0"}}),
                               encoding="utf-8")
        output = self.root / f"{template}-{label}"
        result = build_site(model_path, config_path, ROOT / "templates" / template / "template.json", output)
        self.assertNotEqual("failed", result["status"], result)
        self.assertFalse(result["errors"], result)
        return output, result

    @staticmethod
    def hashes(output):
        return {file.relative_to(output).as_posix(): hashlib.sha256(file.read_bytes()).hexdigest()
                for file in output.rglob("*") if file.is_file()}

    def test_all_five_generate_validate_and_repeat_identically(self):
        model = copy.deepcopy(self.model)
        model["trends"][0]["observations"][1]["value"] = 50
        for template in BUILTIN_TEMPLATE_IDS:
            with self.subTest(template=template):
                first, _ = self.build(template, model, "first")
                second, _ = self.build(template, model, "second")
                self.assertEqual(self.hashes(first), self.hashes(second))
                validation = validate_site(first)
                self.assertFalse(validation["errors"], validation)
                manifest = load_json(first / "report-manifest.json")
                pages = list(first.glob("*.html"))
                self.assertEqual(len(pages), manifest["pageCount"])
                self.assertEqual(9, manifest["itemCount"])
                for page in pages:
                    text = page.read_text(encoding="utf-8")
                    self.assertIn("Public sample", text)
                    self.assertNotIn("<script", text.lower())
                    self.assertEqual("9", Records(text).body["data-item-count"])

    def test_new_templates_show_missing_and_empty_collections_without_inventing_data(self):
        for template in BUILTIN_TEMPLATE_IDS:
            for empty in (False, True):
                with self.subTest(template=template, empty=empty):
                    model = {key: copy.deepcopy(self.model[key]) for key in ("schemaVersion", "report", "provenance")}
                    model["provenance"]["recordCounts"]["raw"] = 0
                    if empty:
                        model.update(metrics=[], items=[], groups=[], trends=[], highlights=[])
                    output, result = self.build(template, model, f"empty-{empty}")
                    self.assertIn("missing-trends", {issue["code"] for issue in result["warnings"]})
                    revalidated = validate_site(output)
                    self.assertIn("missing-trends", {issue["code"] for issue in revalidated["warnings"]})
                    self.assertEqual(0, load_json(output / "report-manifest.json")["itemCount"])
                    text = (output / "index.html").read_text(encoding="utf-8")
                    self.assertNotIn("Release approved", text)
                    self.assertFalse(Records(text).items)

    def test_action_filters_are_exact_and_full_records_remain_accessible(self):
        output, _ = self.build("action-risk")
        selections = {
            "index.html": {"a", "b", "c", "g", "h", "j"},
            "overdue.html": {"a"},
            "blocked.html": {"a", "h"},
            "due-next-seven-days.html": {"b", "c", "j"},
            "all-records.html": {item["id"] for item in self.model["items"]},
        }
        for name, expected in selections.items():
            with self.subTest(page=name):
                text = (output / name).read_text(encoding="utf-8")
                records = Records(text)
                self.assertEqual(expected, set(records.items))
                self.assertEqual(len(expected), len(records.items), "Repeated/filler rows are forbidden")
                self.assertEqual(str(len(expected)), records.body["data-selected-item-count"])
                self.assertNotIn("All open", text)

    def test_group_details_resolve_both_membership_forms_and_descendants(self):
        output, _ = self.build("portfolio-team")
        index = Records((output / "index.html").read_text(encoding="utf-8"))
        self.assertEqual({"root", "child", "empty"}, set(index.groups))
        for group, expected in {"root": {"a", "b"}, "child": {"b"}, "empty": set()}.items():
            detail = output / index.groups[group]
            records = Records(detail.read_text(encoding="utf-8"))
            self.assertEqual(expected, set(records.items))
            self.assertEqual(len(expected), len(records.items))
            self.assertEqual(str(len(expected)), records.body["data-selected-item-count"])
        all_records = Records((output / "all-records.html").read_text(encoding="utf-8"))
        self.assertEqual(9, len(set(all_records.items)))

    def test_cycle_is_a_structured_validation_error(self):
        self.model["groups"][1]["childGroupIds"] = ["root"]
        report = validate_model(self.model, load_json(ROOT / "templates" / "portfolio-team" / "template.json"))
        self.assertIn("group-cycle", {issue["code"] for issue in report["errors"]})

    def test_new_templates_escape_content_keep_ownership_separate_and_handle_zero_trends(self):
        self.model["items"][0].update({
            "title": "<script>alert('x')</script>",
            "accountableOwner": {"team": "Outcome Owner"},
            "actionOwner": {"displayName": "Action Owner"},
            "dueDate": "2026-09-14", "eta": "2026-09-20",
            "nextAction": "<b>Source next action</b>",
            "links": [{"label": "Untrusted URL", "type": "source", "href": "javascript:alert(1)"}],
        })
        self.model["groups"][0]["page"] = "../../escape.html"
        for template in BUILTIN_TEMPLATE_IDS[1:]:
            with self.subTest(template=template):
                output, _ = self.build(template)
                text = "\n".join(page.read_text(encoding="utf-8") for page in output.glob("*.html"))
                self.assertNotIn("<script>", text)
                self.assertNotIn('href="javascript:', text)
                self.assertIn("Outcome Owner", text)
                self.assertIn("Action Owner", text)
                self.assertIn("2026-09-14", text)
                self.assertIn("2026-09-20", text)
                self.assertIn("&lt;b&gt;Source next action&lt;/b&gt;", text)
                self.assertFalse((self.root / "escape.html").exists())
                self.assertFalse(validate_site(output)["errors"])

    def test_cli_rejects_non_builtin_paths(self):
        command = [sys.executable, "-B", str(ROOT / "scripts" / "build"), "--template", "../executive-health",
                   "--data", "unused", "--config", "unused"]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("invalid choice", result.stderr)


if __name__ == "__main__":
    unittest.main()
