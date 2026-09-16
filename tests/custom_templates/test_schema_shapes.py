"""Regression coverage for ReportKit's deliberately bounded schema subset."""

from __future__ import annotations

import itertools
import json
import re
import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from json_schema import (  # noqa: E402
    MAX_PATTERN_REPEAT,
    MAX_SCHEMA_DEPTH,
    MAX_SCHEMA_NODES,
    VERSION_PATTERN,
    validate_instance,
    validate_schema_definition,
)
from template_pack import validate_pack  # noqa: E402


def invalid_shapes() -> list[tuple[str, object]]:
    cases: list[tuple[str, object]] = []
    for keyword in ("required", "enum"):
        cases.extend((keyword, value) for value in (1, True, None, "value", {}))
    cases.extend(("required", value) for value in ([1], [[]], [{}], ["x", "x"]))
    cases.extend(("enum", value) for value in ([], [1, 1.0], [True, True]))
    cases.extend(("type", value) for value in (1, True, None, {}, [], [[]], [{}], [None], ["bad"], ["string", "string"]))
    for keyword in ("properties", "$defs"):
        cases.extend((keyword, value) for value in (1, None, [], True, {"unused": 1}, {"unused": None}))
    for keyword in ("items", "not"):
        cases.extend((keyword, value) for value in (1, None, [], True, "string"))
    cases.extend(("additionalProperties", value) for value in (1, None, [], "false"))
    for keyword in ("anyOf", "oneOf", "allOf"):
        cases.extend((keyword, value) for value in (1, None, True, {}, [], [None], [True], [1]))
    for keyword in ("minLength", "maxLength", "minItems", "maxItems", "minProperties", "maxProperties"):
        cases.extend((keyword, value) for value in (-1, True, None, 1.5, "1", [], {}))
    for keyword in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum"):
        cases.extend((keyword, value) for value in (True, None, "1", [], {}))
    cases.extend(("uniqueItems", value) for value in (1, None, [], "true"))
    cases.extend(("format", value) for value in (1, None, [], {}, "uri"))
    cases.extend(("pattern", value) for value in (1, None, [], {}))
    for keyword in ("$schema", "$id", "title", "description", "$ref"):
        cases.extend((keyword, value) for value in (1, None, [], {}))
    return cases


class SchemaShapeTests(unittest.TestCase):
    def assert_definition_errors(self, schema: object, path: str | None = None) -> None:
        errors = validate_schema_definition(schema)
        self.assertTrue(errors, schema)
        self.assertTrue(all(set(error) == {"code", "message", "path"} for error in errors), errors)
        if path is not None:
            self.assertTrue(any(error["path"] == path for error in errors), errors)
        # The helper must fail closed even when called outside validate_pack.
        self.assertTrue(validate_instance({}, schema), schema)

    def test_all_keyword_shapes_are_checked_before_evaluation(self) -> None:
        for keyword, value in invalid_shapes():
            with self.subTest(keyword=keyword, value=value):
                self.assert_definition_errors({keyword: value})

    def test_invalid_shapes_are_reported_at_the_keyword(self) -> None:
        for keyword in ("required", "enum", "type", "minimum", "maxItems", "pattern", "$ref"):
            with self.subTest(keyword=keyword):
                self.assert_definition_errors({keyword: 1 if keyword not in ("minimum", "maxItems") else None}, f"$.{keyword}")

    def test_unvisited_nested_schemas_are_validated(self) -> None:
        bad = {"required": 1}
        cases = [
            {"properties": {"unused": bad}},
            {"$defs": {"unused": bad}},
            {"items": bad},
            {"additionalProperties": bad},
            {"not": bad},
            *({keyword: [{}, bad]} for keyword in ("anyOf", "oneOf", "allOf")),
        ]
        for schema in cases:
            with self.subTest(schema=schema):
                self.assert_definition_errors(schema)

    def test_unknown_keywords_and_general_schema_features_are_rejected(self) -> None:
        for keyword in ("patternProperties", "unevaluatedProperties", "prefixItems", "contains", "if", "$dynamicRef", "multipleOf"):
            with self.subTest(keyword=keyword):
                errors = validate_schema_definition({keyword: {}})
                self.assertEqual("json-schema-keyword", errors[0]["code"])
        for schema in (True, False, None, [], 1):
            with self.subTest(schema=schema):
                self.assert_definition_errors(schema)

    def test_checked_in_and_example_schemas_remain_accepted(self) -> None:
        paths = sorted((ROOT / "schema").glob("*.schema.json"))
        paths += sorted((ROOT / "examples").rglob("config.schema.json"))
        self.assertGreaterEqual(len(paths), 9)
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual([], validate_schema_definition(json.loads(path.read_text(encoding="utf-8-sig"))))

    def test_supported_keyword_constraints_are_enforced(self) -> None:
        cases = [
            ({}, {"required": ["x"]}, "required"),
            ({}, {"minProperties": 1}, "min-properties"),
            ({"x": 1}, {"maxProperties": 0}, "max-properties"),
            ([], {"minItems": 1}, "min-items"),
            ([1], {"maxItems": 0}, "max-items"),
            ("", {"minLength": 1}, "min-length"),
            ("xx", {"maxLength": 1}, "max-length"),
            (1, {"minimum": 1.5}, "minimum"),
            (2, {"maximum": 1.5}, "maximum"),
            (1.5, {"exclusiveMinimum": 1.5}, "exclusiveMinimum"),
            (1.5, {"exclusiveMaximum": 1.5}, "exclusiveMaximum"),
            (0, {"enum": [1]}, "enum"),
            (True, {"const": 1}, "const"),
            ([1, 1.0], {"uniqueItems": True}, "unique-items"),
            ([0], {"items": {"minimum": 1}}, "minimum"),
            ({"x": ""}, {"additionalProperties": {"minLength": 1}}, "min-length"),
            ({"x": ""}, {"properties": {"x": {"minLength": 1}}}, "min-length"),
            ({"x": ""}, {"additionalProperties": False}, "additional-property"),
            (1, {"anyOf": [{"type": "string"}, {"type": "boolean"}]}, "anyOf"),
            (1, {"oneOf": [{}, {}]}, "oneOf"),
            (1, {"allOf": [{"minimum": 1}, {"maximum": 0}]}, "allOf"),
            (1, {"not": {"type": "number"}}, "not"),
        ]
        for instance, schema, code in cases:
            with self.subTest(instance=instance, schema=schema):
                self.assertEqual([], validate_schema_definition(schema))
                self.assertIn(f"json-schema-{code}", {error["code"] for error in validate_instance(instance, schema)})

    def test_valid_json_values_and_numeric_boundaries_are_supported(self) -> None:
        cases = [
            (None, {"const": None}),
            ({"nested": [1, True, None]}, {"const": {"nested": [1.0, True, None]}}),
            (True, {"enum": [1, True]}),
            ([1, True], {"uniqueItems": True}),
            (None, {"type": ["string", "null"]}),
            ({}, {"required": [], "additionalProperties": True}),
            (1, {"minimum": 1.0, "maximum": 1.0}),
            (1.5, {"exclusiveMinimum": 1, "exclusiveMaximum": 2}),
            (1, {"anyOf": [{"type": "number"}, {"type": "string"}]}),
            (1, {"oneOf": [{"type": "number"}, {"type": "string"}]}),
            (1, {"allOf": [{"minimum": 1}, {"maximum": 1}]}),
        ]
        for instance, schema in cases:
            with self.subTest(instance=instance, schema=schema):
                self.assertEqual([], validate_instance(instance, schema))

    def test_non_json_values_and_nonfinite_bounds_fail_closed(self) -> None:
        for keyword in ("const", "enum", "default", "minimum", "maximum", "exclusiveMinimum"):
            for value in (float("nan"), float("inf"), float("-inf"), object()):
                with self.subTest(keyword=keyword, value=value):
                    self.assert_definition_errors({keyword: [value] if keyword == "enum" else value})
        self.assert_definition_errors({"properties": {1: {}}})

    def test_reference_targets_and_cycles_are_checked(self) -> None:
        cases = [
            {"$ref": "https://example.invalid/schema"},
            {"$ref": "file:///schema.json"},
            {"$ref": "#"},
            {"$ref": "#/missing"},
            {"$ref": "#/type", "type": "string"},
            {"$ref": "#/$defs/a~2", "$defs": {"a~2": {}}},
            {"$ref": "#/const", "const": {}},
            {"$ref": "#/default", "default": {"required": 1}},
            {"$ref": "#/anyOf/01", "anyOf": [{}, {}]},
            {"$ref": "#/anyOf/999999999999999999999999", "anyOf": [{}]},
            {"$ref": "#/$defs/a", "$defs": {"a": {"$ref": "#/$defs/a"}}},
            {"$defs": {"a": {"$ref": "#/$defs/b"}, "b": {"$ref": "#/$defs/a"}}},
            {"$defs": {"a": {"properties": {"child": {"$ref": "#/$defs/a"}}}}},
        ]
        for schema in cases:
            with self.subTest(schema=schema):
                self.assert_definition_errors(schema)

    def test_valid_local_pointers_and_ref_siblings_are_enforced(self) -> None:
        schemas = [
            {"$defs": {"a/b~c": {"minimum": 1}}, "$ref": "#/$defs/a~1b~0c", "maximum": 2},
            {"anyOf": [{"minimum": 1}], "$ref": "#/anyOf/0", "maximum": 2},
        ]
        for schema in schemas:
            with self.subTest(schema=schema):
                self.assertEqual([], validate_instance(1, schema))
                self.assertTrue(validate_instance(0, schema))
                self.assertIn("json-schema-maximum", {issue["code"] for issue in validate_instance(3, schema)})

    def test_selected_root_subschemas_cannot_bypass_shape_validation(self) -> None:
        root = {"$defs": {"value": {"minimum": 1}}, "properties": {"x": {"items": {"$ref": "#/$defs/value"}}}}
        self.assertEqual([], validate_instance([1], root["properties"]["x"], root_schema=root))
        root = {"default": {"$ref": "#/properties/x", "required": 1}, "properties": {"x": {}}}
        self.assertTrue(validate_instance({}, root["default"], root_schema=root))

    def test_deep_wide_and_exponentially_expanded_schemas_are_bounded(self) -> None:
        nested: dict = {}
        for _ in range(MAX_SCHEMA_DEPTH + 1):
            nested = {"items": nested}
        self.assert_definition_errors(nested)
        self.assert_definition_errors({"properties": {str(index): {} for index in range(MAX_SCHEMA_NODES + 1)}})
        definitions: dict = {"0": {}}
        for index in range(1, 18):
            definitions[str(index)] = {"allOf": [{"$ref": f"#/$defs/{index - 1}"} for _ in range(2)]}
        self.assert_definition_errors({"$defs": definitions, "$ref": "#/$defs/17"})
        chain = {str(index): {"$ref": f"#/$defs/{index + 1}"} for index in range(80)}
        chain["80"] = {}
        self.assert_definition_errors({"$defs": chain, "$ref": "#/$defs/0"})
        cycle: dict = {}
        cycle["items"] = cycle
        self.assert_definition_errors(cycle)

    def test_unsupported_regex_syntax_and_extreme_repetitions_fail_early(self) -> None:
        patterns = [
            "(", "(a+)+$", "a|b", r"(a)\1", r"\1", r"\bword", r"\Aword",
            "[", "\\", "a**", "a{2,1}", "a{9999999999999999999999999}",
            f"a{{{MAX_PATTERN_REPEAT + 1}}}", "a" * 129, "(?=a)a",
            r"\UFFFFFFFF", r"[\UFFFFFFFF]", r"\U00110000", r"\xZZ", r"\uZZZZ",
        ]
        for pattern in patterns:
            with self.subTest(pattern=pattern):
                self.assert_definition_errors({"pattern": pattern})

    def test_safe_pattern_matching_preserves_existing_fullmatch_semantics(self) -> None:
        patterns = [
            "", "^$", "a", ".", "^a*$", "a+b?", "a*a*a*b", r"^[a-z0-9][a-z0-9-]*$",
            r"^#[0-9A-Fa-f]{6}$", r"^[^\\]+\.html$", r"\d{1,3}\.\d+",
            r"a{0,2}b{1,}a?", r"\[a\]", r"[()|]+", r"a\$",
        ]
        values = ["", "a", "b", "aaab", "aabaaa", "1.22", "1234.2", "page.html", "bad\\page.html", "#Ab1234", "a$", "[a]", "()|", "\n"]
        values += ["".join(chars) for count in range(5) for chars in itertools.product("ab", repeat=count)]
        for pattern in patterns:
            self.assertEqual([], validate_schema_definition({"pattern": pattern}), pattern)
            for value in values:
                with self.subTest(pattern=pattern, value=value):
                    self.assertEqual(re.fullmatch(pattern, value) is not None, not validate_instance(value, {"pattern": pattern}))
        for value in ("0.1.2", "12.34.56", "01.1.2", "1.2.3.4"):
            self.assertEqual(re.fullmatch(VERSION_PATTERN, value) is not None, not validate_instance(value, {"pattern": VERSION_PATTERN}))

    def test_pathological_flat_regex_is_linear_and_budget_failures_are_not_negated(self) -> None:
        pattern = "^" + "a*" * 40 + "b$"
        errors = validate_instance("a" * 1000 + "!", {"pattern": pattern})
        self.assertEqual("json-schema-pattern", errors[0]["code"])
        for keyword in ("anyOf", "oneOf", "allOf", "not"):
            child = {"pattern": "a*a*a*a*b"}
            schema = {keyword: child if keyword == "not" else [{}, child]}
            with self.subTest(keyword=keyword), patch("json_schema.MAX_PATTERN_STEPS", 10):
                errors = validate_instance("a" * 100, schema)
                self.assertEqual("json-schema-budget", errors[0]["code"])
        with patch("json_schema.MAX_VALIDATION_STEPS", 20):
            errors = validate_instance([1] * 10, {"items": {"allOf": [{}, {}, {}]}})
            self.assertEqual("json-schema-budget", errors[0]["code"])


class SchemaShapePackCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project = ROOT / "examples" / "custom-template-project"
        self.source = self.project / "templates" / "contoso-release-review"
        self.workspace = ROOT / "tests" / "custom_templates" / f".schema-shapes-{uuid.uuid4().hex}"
        self.pack = self.workspace / "pack"
        shutil.copytree(self.source, self.pack)
        self.addCleanup(shutil.rmtree, self.workspace)

    def set_schema(self, schema: object) -> None:
        (self.pack / "config.schema.json").write_text(json.dumps(schema), encoding="utf-8")

    def test_pack_rejects_each_malformed_keyword_shape(self) -> None:
        for keyword, value in invalid_shapes():
            with self.subTest(keyword=keyword, value=value):
                self.set_schema({keyword: value})
                report, pack = validate_pack(self.pack)
                self.assertIsNone(pack)
                self.assertEqual("failed", report["status"])
                self.assertTrue(any(error["code"].startswith("pack-custom-json-schema-") for error in report["errors"]), report)

    def test_validate_and_build_cli_report_invalid_schemas_without_tracebacks(self) -> None:
        expanded: dict = {"0": {}}
        for index in range(1, 18):
            expanded[str(index)] = {"anyOf": [{"$ref": f"#/$defs/{index - 1}"} for _ in range(2)]}
        schemas = [
            {"required": 1},
            {"enum": 1},
            {"type": [[]]},
            {"properties": {"unused": {"enum": 1}}},
            {"items": None},
            {"anyOf": [None]},
            {"allOf": 1},
            {"minimum": "zero"},
            {"pattern": "(a+)+$"},
            {"pattern": "a{9999999999999999999999999}"},
            {"pattern": r"\UFFFFFFFF"},
            {"$defs": {"loop": {"$ref": "#/$defs/loop"}}},
            {"$defs": expanded, "$ref": "#/$defs/17"},
            {"$ref": "https://example.invalid/schema"},
        ]
        output = self.workspace / "site"
        output.mkdir()
        sentinel = output / "unchanged.txt"
        sentinel.write_text("Preserve previous output.", encoding="utf-8")
        for schema in schemas:
            self.set_schema(schema)
            commands = [
                ["validate-template", str(self.pack)],
                [
                    "build-template", "--template", str(self.pack),
                    "--data", str(self.source / "examples" / "canonical-report.json"),
                    "--config", str(self.source / "examples" / "configuration.json"),
                    "--lock", str(self.project / "reportkit.lock.json"),
                    "--output", str(output), "--overwrite",
                ],
            ]
            for script, *arguments in commands:
                with self.subTest(schema=schema, script=script):
                    result = subprocess.run(
                        [sys.executable, "-B", str(SCRIPTS / script), *arguments],
                        cwd=ROOT, capture_output=True, text=True, timeout=15, check=False,
                    )
                    self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                    self.assertNotIn("Traceback", result.stdout + result.stderr)
                    self.assertIn("pack-custom-json-schema-", result.stdout)
                    if script == "validate-template":
                        self.assertEqual("failed", json.loads(result.stdout)["status"])
                    self.assertEqual("Preserve previous output.", sentinel.read_text(encoding="utf-8"))
                    self.assertEqual([sentinel], list(output.iterdir()))


if __name__ == "__main__":
    unittest.main()
