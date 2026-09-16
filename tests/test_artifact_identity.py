"""Synthetic contracts for content identities and implemented capabilities."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import artifact_identity
from artifact_identity import canonical_digest, make_reproducibility, renderer_identity, validate_capabilities, verify_identity
from json_schema import validate_instance, validate_schema_definition
from reportkit_engine import build_site, load_json, write_json
from site_inventory import inspect_site_inventory
from template_pack import REQUIRED_FILES, _json_file, build_pack_site, validate_pack


class ArtifactIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = ROOT / f".identity-test-{uuid.uuid4().hex}"
        self.workspace.mkdir()
        self.addCleanup(shutil.rmtree, self.workspace)
        self.site = self.workspace / "site"
        self.site.mkdir()
        self.model = {
            "schemaVersion": "1.0",
            "report": {
                "id": "synthetic-report", "title": "Synthetic health", "status": "healthy",
                "classification": "Public sample", "generatedAt": "2026-09-15T18:00:00Z",
                "dataAsOf": "2026-09-15T17:00:00Z",
            },
            "metrics": [{"id": "synthetic-count", "label": "Synthetic count", "value": 1, "unit": "records"}],
            "groups": [{"id": "synthetic-group", "label": "Synthetic group", "itemIds": ["synthetic-item"]}],
            "items": [{"id": "synthetic-item", "title": "Synthetic item", "status": "healthy"}],
            "provenance": {
                "adapter": {"id": "synthetic-adapter", "version": "1.0"},
                "sources": [{"type": "fixture", "name": "Synthetic records", "recordCount": 1}],
                "recordCounts": {"raw": 1},
            },
        }
        self.config = {"version": "1.0", "template": {"id": "executive-health", "version": "1.0"}}

    def make_manifest(self):
        (self.site / "index.html").write_bytes(b"synthetic\r\nhtml")
        write_json(self.site / "validation-report.json", {"status": "passed"})
        identity = make_reproducibility(self.model, self.config, self.site)
        manifest = {
            "files": ["index.html", "report-manifest.json", "validation-report.json"],
            "reproducibility": identity,
        }
        write_json(self.site / "report-manifest.json", manifest)
        files, errors = inspect_site_inventory(self.site)
        self.assertEqual([], errors)
        return manifest, files

    def test_canonical_digest_is_compact_utf8_sorted_json(self) -> None:
        first = {"z": [1, {"b": False, "a": "é"}], "a": None}
        second = {"a": None, "z": [1, {"a": "é", "b": False}]}
        expected = hashlib.sha256('{"a":null,"z":[1,{"a":"é","b":false}]}'.encode("utf-8")).hexdigest()
        self.assertEqual("sha256:" + expected, canonical_digest(first))
        self.assertEqual(canonical_digest(first), canonical_digest(second))
        self.assertNotEqual(canonical_digest(first), canonical_digest({"a": None}))
        with self.assertRaises(ValueError):
            canonical_digest(float("nan"))

    def test_renderer_digest_is_checkout_independent_and_line_ending_normalized(self) -> None:
        roots = [self.workspace / "first", self.workspace / "second"]
        for root, newline in zip(roots, [b"\n", b"\r\n"]):
            (root / "scripts").mkdir(parents=True)
            (root / "schema").mkdir()
            for name in artifact_identity._RENDERER_SOURCES:
                (root / "scripts" / name).write_bytes(b"synthetic" + newline + name.encode("utf-8") + newline)
            (root / "schema" / "synthetic.schema.json").write_bytes(b"{}" + newline)
        with patch.object(artifact_identity, "ROOT", roots[0]):
            first = renderer_identity()
        with patch.object(artifact_identity, "ROOT", roots[1]):
            self.assertEqual(first, renderer_identity())
            self.assertEqual({"id", "digest"}, set(first))
            for relative in [
                *(Path("scripts") / name for name in artifact_identity._RENDERER_SOURCES),
                Path("schema") / "synthetic.schema.json",
            ]:
                with self.subTest(relative=relative):
                    path = roots[1] / relative
                    original = path.read_bytes()
                    path.write_bytes(original + b"changed")
                    self.assertNotEqual(first, renderer_identity())
                    path.write_bytes(original)

    def test_identity_hashes_raw_output_and_correct_provenance_shape(self) -> None:
        manifest, files = self.make_manifest()
        identity = manifest["reproducibility"]
        self.assertEqual(canonical_digest(self.model), identity["canonicalModelDigest"])
        self.assertEqual(canonical_digest(self.config), identity["configurationDigest"])
        self.assertEqual(
            ["adapter:synthetic-adapter@1.0", "source:fixture:Synthetic records"],
            identity["sourceIdentifiers"],
        )
        self.assertEqual({"index.html", "validation-report.json"}, set(identity["artifactHashes"]))
        self.assertEqual("sha256:" + hashlib.sha256(b"synthetic\r\nhtml").hexdigest(), identity["artifactHashes"]["index.html"])
        self.assertEqual([], verify_identity(manifest, self.site, files))
        self.assertEqual(identity, make_reproducibility(self.model, self.config, self.site))

    def test_source_identifiers_are_sorted_unique_descriptive_claims(self) -> None:
        self.model["provenance"]["sources"] *= 2
        self.model["provenance"]["sources"].append({"type": "alpha", "name": "Fixture"})
        manifest, files = self.make_manifest()
        sources = manifest["reproducibility"]["sourceIdentifiers"]
        self.assertEqual(sorted(set(sources)), sources)
        manifest["reproducibility"]["canonicalModelDigest"] = "sha256:" + "0" * 64
        manifest["reproducibility"]["configurationDigest"] = "sha256:" + "1" * 64
        manifest["reproducibility"]["renderer"]["digest"] = "sha256:" + "2" * 64
        self.assertEqual([], verify_identity(manifest, self.site, files), "Reported inputs are not on-site attestations.")

    def test_validation_report_rewrite_requires_identity_refresh(self) -> None:
        manifest, files = self.make_manifest()
        write_json(self.site / "validation-report.json", {"status": "passed-with-warnings"})
        errors = verify_identity(manifest, self.site, files)
        self.assertEqual([("identity-artifact-mismatch", "validation-report.json")], [(error["code"], error["path"]) for error in errors])
        manifest["reproducibility"] = make_reproducibility(self.model, self.config, self.site)
        self.assertEqual([], verify_identity(manifest, self.site, files))

    def test_artifact_hashes_require_exact_set_and_exclude_manifest(self) -> None:
        manifest, files = self.make_manifest()
        for name, remove in [("index.html", True), ("extra.json", False), ("report-manifest.json", False)]:
            with self.subTest(name=name):
                changed = copy.deepcopy(manifest)
                hashes = changed["reproducibility"]["artifactHashes"]
                if remove:
                    del hashes[name]
                else:
                    hashes[name] = "sha256:" + "0" * 64
                with patch.object(artifact_identity, "_artifact_digest", side_effect=AssertionError("Bad sets must not be read")):
                    errors = verify_identity(changed, self.site, files)
                self.assertEqual("identity-artifact-set", errors[0]["code"])

    def test_malformed_identity_is_structured_without_artifact_reads(self) -> None:
        manifest, files = self.make_manifest()
        for field, value in [
            ("canonicalModelDigest", "not-a-digest"), ("renderer", {"id": "renderer"}),
            ("sourceIdentifiers", ["duplicate", "duplicate"]), ("artifactHashes", {"index.html": 123}),
        ]:
            with self.subTest(field=field):
                changed = copy.deepcopy(manifest)
                changed["reproducibility"][field] = value
                with patch.object(artifact_identity, "_artifact_digest", side_effect=AssertionError("Malformed identity must not be read")):
                    self.assertTrue(verify_identity(changed, self.site, files))

    def test_untrusted_manifest_paths_never_become_read_paths(self) -> None:
        manifest, files = self.make_manifest()
        manifest["files"].append("../outside.json")
        with patch.object(artifact_identity, "_artifact_digest", side_effect=AssertionError("Invalid manifest must not be read")):
            errors = verify_identity(manifest, self.site, files)
        self.assertEqual("identity-file-set", errors[0]["code"])
        write_json(self.site / "report-manifest.json", manifest)
        with self.assertRaises(ValueError):
            make_reproducibility(self.model, self.config, self.site)

    def test_unvalidated_inventory_paths_and_read_failures_are_structured(self) -> None:
        manifest, files = self.make_manifest()
        for path in [self.workspace / "outside.json", self.site / ".." / "outside.json", self.site / "payload.EXE"]:
            with self.subTest(path=path), patch.object(artifact_identity, "_artifact_digest", side_effect=AssertionError("Must not read outside inventory")):
                self.assertEqual("identity-inventory", verify_identity(manifest, self.site, [*files, path])[0]["code"])
        with patch.object(artifact_identity, "_artifact_digest", side_effect=PermissionError("denied")):
            self.assertEqual({"identity-artifact-read"}, {error["code"] for error in verify_identity(manifest, self.site, files)})

    def test_changed_file_type_is_rechecked_without_opening(self) -> None:
        manifest, files = self.make_manifest()
        path = self.site / "index.html"
        path.unlink()
        path.mkdir()
        errors = verify_identity(manifest, self.site, files)
        self.assertIn(("identity-artifact-read", "index.html"), [(error["code"], error["path"]) for error in errors])

    def test_make_identity_rejects_unsupported_entries(self) -> None:
        (self.site / "payload.zip").write_bytes(b"synthetic")
        with self.assertRaises(ValueError):
            make_reproducibility(self.model, self.config, self.site)

    def test_capability_aliases_and_optional_design_are_independent(self) -> None:
        capability = load_json(ROOT / "templates" / "executive-health" / "template.json")
        self.assertEqual([], validate_capabilities(capability))
        self.assertFalse(capability["implementationCapabilities"]["multiPage"])
        self.assertTrue(capability["designCapabilities"]["multiPage"])
        legacy = copy.deepcopy(capability)
        del legacy["implementationCapabilities"]
        del legacy["designCapabilities"]
        self.assertEqual([], validate_capabilities(legacy))
        modern = copy.deepcopy(capability)
        del modern["features"]
        self.assertEqual([], validate_capabilities(modern))
        capability["features"]["multiPage"] = True
        self.assertIn("capability-alias-mismatch", {error["code"] for error in validate_capabilities(capability)})
        modern["implementationCapabilities"]["multiPage"] = "future"
        self.assertTrue(validate_capabilities(modern))

    def test_schema_contracts_are_supported_and_require_reproducibility(self) -> None:
        for name in ["template-capability-v1.schema.json", "report-manifest-v1.schema.json"]:
            schema = load_json(ROOT / "schema" / name)
            self.assertEqual([], validate_schema_definition(schema), name)
        schema = load_json(ROOT / "schema" / "report-manifest-v1.schema.json")
        self.assertIn("reproducibility", schema["required"])
        self.assertTrue(validate_instance({}, schema))

    def test_all_builtin_implemented_capabilities_match_generated_page_counts(self) -> None:
        model_path = self.workspace / "model.json"
        config_path = self.workspace / "config.json"
        write_json(model_path, self.model)
        contracts = {
            "executive-health": 1, "operational-health": 1, "compliance-readiness": 1,
            "action-risk": 5, "portfolio-team": 3,
        }
        for template, count in contracts.items():
            with self.subTest(template=template):
                capability_path = ROOT / "templates" / template / "template.json"
                capability = load_json(capability_path)
                self.assertEqual([], validate_capabilities(capability))
                self.assertEqual(count > 1, capability["implementationCapabilities"]["multiPage"])
                self.assertEqual(capability["features"], capability["implementationCapabilities"])
                self.assertTrue(capability["designCapabilities"]["multiPage"])
                config = {"version": "1.0", "template": {"id": template, "version": capability["version"]}}
                write_json(config_path, config)
                output = self.workspace / template
                report = build_site(model_path, config_path, capability_path, output)
                self.assertFalse(report["errors"], report)
                manifest = load_json(output / "report-manifest.json")
                self.assertEqual(count, manifest["pageCount"])
                files, errors = inspect_site_inventory(output)
                self.assertEqual([], errors)
                self.assertEqual([], verify_identity(manifest, output, files))
                self.assertEqual(canonical_digest(config), manifest["reproducibility"]["configurationDigest"])

    def test_custom_implementation_rejects_multipage_but_design_can_describe_it(self) -> None:
        source = ROOT / "examples" / "custom-template-project" / "templates" / "contoso-release-review"
        pack_path = self.workspace / "pack"
        shutil.copytree(source, pack_path)
        template_path = pack_path / "template.json"
        template = load_json(template_path)
        template["designCapabilities"] = {**template["implementationCapabilities"], "multiPage": True}
        write_json(template_path, template)
        report, _ = validate_pack(pack_path)
        self.assertFalse(report["errors"], report)
        template["implementationCapabilities"]["multiPage"] = True
        template["features"]["multiPage"] = True
        write_json(template_path, template)
        report, _ = validate_pack(pack_path)
        self.assertIn("pack-implementation-scope", {error["code"] for error in report["errors"]})

    def test_custom_build_refreshes_hashes_after_replacement_warnings(self) -> None:
        project = ROOT / "examples" / "custom-template-project"
        pack_path = project / "templates" / "contoso-release-review"
        model_path = self.workspace / "model.json"
        config_path = self.workspace / "config.json"
        write_json(model_path, self.model)
        write_json(config_path, {"version": "1.0", "template": {"id": "contoso/release-review", "version": "1.0.0"}})
        output = self.workspace / "custom-output"
        from template_pack import replace_output

        def replace_with_warning(temporary, destination, backup):
            return [*replace_output(temporary, destination, backup), {"code": "synthetic-warning", "message": "Synthetic replacement warning.", "path": "."}]

        with patch("template_pack.replace_output", side_effect=replace_with_warning):
            report = build_pack_site(pack_path, model_path, config_path, output, project / "reportkit.lock.json")
        self.assertFalse(report["errors"], report)
        manifest = load_json(output / "report-manifest.json")
        files, errors = inspect_site_inventory(output)
        self.assertFalse(errors)
        self.assertEqual([], verify_identity(manifest, output, files))
        self.assertIn("synthetic-warning", {error["code"] for error in load_json(output / "validation-report.json")["warnings"]})

    def test_pack_json_is_bounded_and_config_schema_is_required(self) -> None:
        self.assertIn("config.schema.json", REQUIRED_FILES)
        for content in [
            b'{"value": NaN}', b'{"value": Infinity}',
            b'{"value":' + b"[" * 80 + b"0" + b"]" * 80 + b"}",
            b'{"value":' + b"[" * 2000 + b"0" + b"]" * 2000 + b"}",
        ]:
            with self.subTest(content=content[:30]):
                errors = []
                self.assertIsNone(_json_file({"test.json": content}, "test.json", errors))
                self.assertEqual("pack-json", errors[0]["code"])
        with patch("template_pack.MAX_FILE_BYTES", 8):
            errors = []
            self.assertIsNone(_json_file({"test.json": b'{"value":0}'}, "test.json", errors))
            self.assertEqual("pack-json", errors[0]["code"])

    def test_pack_deadline_can_expire_before_loading(self) -> None:
        with patch("template_pack.time.monotonic", side_effect=[0.0, 10.0]), patch("template_pack.load_pack") as loader:
            report, pack = validate_pack(self.workspace / "unused")
        loader.assert_not_called()
        self.assertIsNone(pack)
        self.assertEqual(["pack-budget"], [error["code"] for error in report["errors"]])

    def test_pack_deadline_is_checked_after_individual_schema_validation(self) -> None:
        source = ROOT / "examples" / "custom-template-project" / "templates" / "contoso-release-review"
        clock = [0.0]

        def slow_schema(template):
            clock[0] = 11.0
            return []

        with (
            patch("template_pack.time.monotonic", side_effect=lambda: clock[0]),
            patch("template_pack.validate_capabilities", side_effect=slow_schema),
            patch("template_pack._validate_template") as semantic_validation,
        ):
            report, pack = validate_pack(source)
        semantic_validation.assert_not_called()
        self.assertIsNone(pack)
        self.assertEqual(["pack-budget"], [error["code"] for error in report["errors"]])

    def test_pack_deadline_stops_before_next_example_validation(self) -> None:
        source = ROOT / "examples" / "custom-template-project" / "templates" / "contoso-release-review"
        clock = [0.0]

        def slow_example(model, template):
            clock[0] = 11.0
            return {"errors": []}

        with (
            patch("template_pack.time.monotonic", side_effect=lambda: clock[0]),
            patch("template_pack.validate_model", side_effect=slow_example) as validation,
        ):
            report, pack = validate_pack(source)
        self.assertEqual(1, validation.call_count)
        self.assertIsNone(pack)
        self.assertEqual(["pack-budget"], [error["code"] for error in report["errors"]])

    def test_pack_deadline_is_cooperative_after_filesystem_work(self) -> None:
        clock = [0.0]

        def slow_load(path, deadline):
            clock[0] = 11.0
            return {}, []

        with (
            patch("template_pack.time.monotonic", side_effect=lambda: clock[0]),
            patch("template_pack.load_pack", side_effect=slow_load),
        ):
            report, pack = validate_pack(self.workspace)
        self.assertIsNone(pack)
        self.assertEqual(["pack-budget"], [error["code"] for error in report["errors"]])


if __name__ == "__main__":
    unittest.main()
