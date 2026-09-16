"""Portable checkout and public-distribution metadata checks."""

import json
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MENU_CHOICES = [
    ("1", "Start a new report"),
    ("2", "Inspect an existing ReportKit project and continue manually"),
    ("3", "Validate a custom template"),
]


class DistributionHygieneTests(unittest.TestCase):
    def test_menu_first_skill_and_ui_metadata_are_present(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        opening = skill.split("## Start here", 1)[1].split("## Guided path", 1)[0]
        choices = re.findall(r"^>\s+(\d+)\.\s+(.+)$", opening, re.MULTILINE)
        self.assertEqual(choices, MENU_CHOICES)
        self.assertIn("Stop after the menu and wait.", opening)
        self.assertGreater(opening.index("Stop after the menu and wait."), opening.index(MENU_CHOICES[-1][1]))
        self.assertIn("do not scan the workspace", opening)
        self.assertIn("Do not show the", opening)
        self.assertNotRegex(opening, r"Resume a report|Add a custom template")
        metadata = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("display_name:", metadata)
        self.assertIn("default_prompt:", metadata)
        self.assertIn("$reportkit", metadata)
        for _, label in MENU_CHOICES:
            self.assertIn(label, metadata)
        self.assertIn("Stop and wait for my selection.", metadata)

    def test_readme_installs_complete_skill_without_overwriting(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        install = readme.split("### 1. Make the skill available", 1)[1].split("## Repository status", 1)[0]
        self.assertIn("**entire repository**", install)
        self.assertIn("Do not copy `SKILL.md` alone", install)
        for folder in ("scripts/", "schema/", "docs/", "agents/", "templates/", "examples/"):
            self.assertIn(f"`{folder}`", install)
        examples = [
            block for block in re.findall(r"```powershell\n(.*?)```", install, re.DOTALL)
            if "git clone" in block
        ]
        self.assertEqual(len(examples), 2)
        self.assertIn("'.github\\skills\\reportkit'", examples[0])
        self.assertIn("$HOME '.copilot\\skills\\reportkit'", examples[1])
        for example in examples:
            self.assertIn("Test-Path -LiteralPath $skillRoot", example)
            self.assertIn("throw 'Skill folder already exists", example)
            self.assertIn('git clone https://github.com/microsoft/ReportKit.git "$skillRoot"', example)
            self.assertLess(example.index("Test-Path"), example.index("git clone"))
            self.assertNotIn("\ncopilot", example)
            self.assertNotIn("Remove-Item", example)
        self.assertIn("**host project's root**", install)
        self.assertIn("Set-Location -LiteralPath $skillRoot", install)
        self.assertIn("Do not install both copies", install)
        self.assertIn("/skills reload", install)
        self.assertIn("/skills info reportkit", install)
        self.assertIn("Use the /reportkit skill.", install)
        self.assertIn("https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills", install)
        self.assertIn("**installed skill root**", install)

    def test_manual_inspection_does_not_inherit_project_authority(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        state = skill.split("## Project state", 1)[1].split("## Read details", 1)[0]
        state = " ".join(state.split())
        for required in (
            "manual inspection, not automated resume",
            "Do not automatically traverse project references",
            "user explicitly requests that specific safe, scoped relative reference",
            "Reject absolute paths",
            "traversal (`..`)",
            "symlinks",
            "junctions",
            "reparse-point paths",
            "linked ancestor directories",
            "prior approvals",
        ):
            self.assertIn(required, state)

    def test_completion_requires_verified_clickable_artifacts(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        completion = " ".join(skill.split("## Completion response", 1)[1].split())
        self.assertIn("Verify each artifact exists", completion)
        self.assertIn("clickable Markdown links", completion)
        for artifact in ("index.html", "report-manifest.json", "validation-report.json"):
            self.assertIn(f"`{artifact}`", completion)
        for required in (
            "actual existing output paths",
            "ZIP was explicitly requested and created",
            "verify it exists",
            "clickable ZIP link",
            "Never return placeholder links",
            "local-file link",
            "loopback-only local server",
            "Verify the server before linking",
            "GitHub source links are not live rendered pages",
            "Pages deployment is not implemented",
        ):
            self.assertIn(required, completion)

    def test_onboarding_docs_keep_menu_and_runtime_boundaries(self):
        for relative in ("README.md", "docs/custom-templates-guided-build.md", "docs/product-contract.md"):
            with self.subTest(document=relative):
                document = (ROOT / relative).read_text(encoding="utf-8")
                choices = re.findall(
                    r"^(\d+)\.\s+(Start a new report|Inspect an existing ReportKit project and continue manually|Validate a custom template)$",
                    document, re.MULTILINE,
                )
                self.assertEqual(choices, MENU_CHOICES)
                for artifact in ("index.html", "report-manifest.json", "validation-report.json"):
                    self.assertIn(f"`{artifact}`", document)
                self.assertIn("manual", document)
                self.assertIn("not implemented", document)
        for relative in (
            "README.md", "SKILL.md", "docs/custom-templates-guided-build.md",
            "docs/implementation-plan.md", "docs/product-contract.md",
            "docs/template-authoring.md", "docs/test-strategy.md",
        ):
            with self.subTest(document=relative):
                document = (ROOT / relative).read_text(encoding="utf-8")
                self.assertNotRegex(document, r"\b(?:34|42|43)\s+(?:automated\s+)?tests?\b")
                self.assertNotRegex(document, r"[A-Z]:\\")

    def test_executable_documentation_examples_match_current_schemas(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            from json_schema import validate_instance
            from reportkit_engine import validate_model

            capability = json.loads((ROOT / "templates" / "executive-health" / "template.json").read_text(encoding="utf-8"))
            model_schema = json.loads((ROOT / "schema" / "reportkit-v1.schema.json").read_text(encoding="utf-8"))
            config_schema = json.loads((ROOT / "schema" / "configuration-v1.schema.json").read_text(encoding="utf-8"))
            for relative in ("README.md", "docs/product-contract.md"):
                document = (ROOT / relative).read_text(encoding="utf-8")
                examples = [json.loads(block) for block in re.findall(r"```json\n(.*?)```", document, re.DOTALL)]
                model = next(example for example in examples if "report" in example and "schemaVersion" in example)
                with self.subTest(document=relative):
                    self.assertEqual(validate_instance(model, model_schema), [])
                    self.assertEqual(validate_model(model, capability)["errors"], [])
                if relative == "docs/product-contract.md":
                    config = next(example for example in examples if "freshnessThresholdsMinutes" in example)
                    self.assertEqual(validate_instance(config, config_schema), [])
            authoring = (ROOT / "docs" / "template-authoring.md").read_text(encoding="utf-8")
            fragment = json.loads(re.search(r"```json\n(.*?)```", authoring, re.DOTALL).group(1))
            for field in ("features", "implementationCapabilities", "designCapabilities"):
                self.assertEqual(fragment[field], capability[field])
        finally:
            sys.path.pop(0)

    def test_visual_lock_only_uses_public_registry(self):
        lock = json.loads((ROOT / "tests" / "visual" / "package-lock.json").read_text(encoding="utf-8"))
        for name, entry in lock["packages"].items():
            if entry.get("resolved"):
                self.assertTrue(entry["resolved"].startswith("https://registry.npmjs.org/"), name)
                self.assertTrue(entry.get("integrity"), name)

    def test_actions_are_pinned_to_commit_shas(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        uses = re.findall(r"uses:\s+([^\s#]+)", workflow)
        self.assertTrue(uses)
        for action in uses:
            self.assertRegex(action, r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}$")
        self.assertIn("scripts/build-examples --overwrite", workflow)
        self.assertIn("scripts/check-generated-clean.py", workflow)
        self.assertNotIn("git diff --exit-code", workflow)


if __name__ == "__main__":
    unittest.main()
