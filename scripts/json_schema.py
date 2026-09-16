"""Small dependency-free JSON Schema evaluator for ReportKit's checked-in contracts."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

MAX_SCHEMA_DEPTH = 20
MAX_SCHEMA_NODES = 500
MAX_PATTERN_LENGTH = 128
ALLOWED_SCHEMA_KEYWORDS = {
    "$schema", "$id", "$defs", "$ref", "title", "description", "default",
    "type", "const", "enum", "properties", "additionalProperties", "required",
    "minProperties", "items", "minItems", "uniqueItems", "minLength", "maxLength",
    "pattern", "format", "minimum", "maximum", "anyOf", "oneOf", "not",
}
ALLOWED_TYPES = {"object", "array", "string", "boolean", "integer", "number", "null"}
ALLOWED_FORMATS = {"date", "date-time"}


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    return False


def _resolve(root: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise ValueError(f"Only local schema references are supported: {reference}")
    current: Any = root
    for segment in reference[2:].split("/"):
        current = current[segment.replace("~1", "/").replace("~0", "~")]
    if not isinstance(current, dict):
        raise ValueError(f"Schema reference does not resolve to an object: {reference}")
    return current


def validate_schema_definition(schema: Any) -> list[dict[str, str]]:
    """Validate the bounded JSON Schema subset accepted from declarative packs."""
    errors: list[dict[str, str]] = []
    nodes = 0

    def add(code: str, text: str, path: str) -> None:
        errors.append({"code": code, "message": text, "path": path})

    def walk(value: Any, path: str, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > MAX_SCHEMA_NODES:
            add("json-schema-too-large", f"Schema exceeds {MAX_SCHEMA_NODES} nodes.", path)
            return
        if depth > MAX_SCHEMA_DEPTH:
            add("json-schema-too-deep", f"Schema exceeds depth {MAX_SCHEMA_DEPTH}.", path)
            return
        if not isinstance(value, dict):
            add("json-schema-definition", "Every schema node must be an object.", path)
            return
        for keyword in sorted(set(value) - ALLOWED_SCHEMA_KEYWORDS):
            add("json-schema-keyword", f"Unsupported schema keyword '{keyword}'.", f"{path}.{keyword}")
        expected = value.get("type")
        if expected is not None:
            expected_types = [expected] if isinstance(expected, str) else expected
            if (
                not isinstance(expected_types, list)
                or not expected_types
                or any(item not in ALLOWED_TYPES for item in expected_types)
            ):
                add("json-schema-definition", "type must use supported JSON types.", f"{path}.type")
        reference = value.get("$ref")
        if reference is not None:
            if not isinstance(reference, str) or not reference.startswith("#/"):
                add("json-schema-ref", "Only local JSON Pointer references are supported.", f"{path}.$ref")
            else:
                try:
                    _resolve(schema, reference)
                except (KeyError, TypeError, ValueError) as exception:
                    add("json-schema-ref", f"Invalid schema reference: {exception}", f"{path}.$ref")
        pattern = value.get("pattern")
        if pattern is not None:
            if not isinstance(pattern, str) or len(pattern) > MAX_PATTERN_LENGTH:
                add("json-schema-pattern-definition", f"pattern must be at most {MAX_PATTERN_LENGTH} characters.", f"{path}.pattern")
            elif any(token in pattern for token in ("(", ")", "|")) or re.search(r"\\[1-9]", pattern):
                add("json-schema-pattern-definition", "Pattern groups, alternation, and backreferences are not supported.", f"{path}.pattern")
            else:
                try:
                    re.compile(pattern)
                except re.error as exception:
                    add("json-schema-pattern-definition", f"Invalid regular expression: {exception}", f"{path}.pattern")
        format_name = value.get("format")
        if format_name is not None and format_name not in ALLOWED_FORMATS:
            add("json-schema-format-definition", f"Unsupported format '{format_name}'.", f"{path}.format")
        properties = value.get("properties")
        if properties is not None:
            if not isinstance(properties, dict):
                add("json-schema-definition", "properties must be an object.", f"{path}.properties")
            else:
                for name, child in properties.items():
                    if not isinstance(name, str):
                        add("json-schema-definition", "Property names must be strings.", f"{path}.properties")
                    else:
                        walk(child, f"{path}.properties.{name}", depth + 1)
        definitions = value.get("$defs")
        if definitions is not None:
            if not isinstance(definitions, dict):
                add("json-schema-definition", "$defs must be an object.", f"{path}.$defs")
            else:
                for name, child in definitions.items():
                    walk(child, f"{path}.$defs.{name}", depth + 1)
        additional = value.get("additionalProperties")
        if additional is not None and not isinstance(additional, bool):
            walk(additional, f"{path}.additionalProperties", depth + 1)
        items = value.get("items")
        if items is not None:
            walk(items, f"{path}.items", depth + 1)
        for keyword in ("anyOf", "oneOf"):
            candidates = value.get(keyword)
            if candidates is not None:
                if not isinstance(candidates, list) or not candidates:
                    add("json-schema-definition", f"{keyword} must be a non-empty array.", f"{path}.{keyword}")
                else:
                    for index, child in enumerate(candidates):
                        walk(child, f"{path}.{keyword}[{index}]", depth + 1)
        if "not" in value:
            walk(value["not"], f"{path}.not", depth + 1)

    walk(schema, "$", 0)

    def follow_references(value: Any, path: str, stack: tuple[str, ...]) -> None:
        if not isinstance(value, dict):
            return
        reference = value.get("$ref")
        if isinstance(reference, str) and reference.startswith("#/"):
            if reference in stack:
                add("json-schema-recursive-ref", "Recursive schema references are not supported.", f"{path}.$ref")
                return
            try:
                follow_references(_resolve(schema, reference), reference, stack + (reference,))
            except (KeyError, TypeError, ValueError):
                return
        for keyword in ("properties", "$defs"):
            children = value.get(keyword, {})
            if isinstance(children, dict):
                for name, child in children.items():
                    follow_references(child, f"{path}.{keyword}.{name}", stack)
        if isinstance(value.get("additionalProperties"), dict):
            follow_references(value["additionalProperties"], f"{path}.additionalProperties", stack)
        if isinstance(value.get("items"), dict):
            follow_references(value["items"], f"{path}.items", stack)
        for keyword in ("anyOf", "oneOf"):
            if isinstance(value.get(keyword), list):
                for index, child in enumerate(value[keyword]):
                    follow_references(child, f"{path}.{keyword}[{index}]", stack)
        if isinstance(value.get("not"), dict):
            follow_references(value["not"], f"{path}.not", stack)

    if isinstance(schema, dict):
        follow_references(schema, "$", ())
    return errors


def _valid_format(value: str, format_name: str) -> bool:
    try:
        if format_name == "date":
            return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d") == value
        if format_name == "date-time":
            instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return "T" in value and instant.utcoffset() is not None
    except ValueError:
        return False
    return True


def validate_instance(
    instance: Any,
    schema: dict[str, Any],
    *,
    root_schema: dict[str, Any] | None = None,
    path: str = "$",
    _ref_stack: tuple[str, ...] = (),
) -> list[dict[str, str]]:
    root_schema = root_schema or schema
    if "$ref" in schema:
        reference = schema["$ref"]
        if not isinstance(reference, str) or reference in _ref_stack:
            return [{"code": "json-schema-ref", "message": "Invalid or recursive schema reference.", "path": path}]
        try:
            target = _resolve(root_schema, reference)
        except (KeyError, TypeError, ValueError) as exception:
            return [{"code": "json-schema-ref", "message": f"Invalid schema reference: {exception}", "path": path}]
        return validate_instance(
            instance,
            target,
            root_schema=root_schema,
            path=path,
            _ref_stack=_ref_stack + (reference,),
        )

    errors: list[dict[str, str]] = []
    if "const" in schema and instance != schema["const"]:
        errors.append({"code": "json-schema-const", "message": f"Value must equal {schema['const']!r}.", "path": path})
    if "enum" in schema and instance not in schema["enum"]:
        errors.append({"code": "json-schema-enum", "message": f"Value is not one of {schema['enum']!r}.", "path": path})

    expected = schema.get("type")
    if expected is not None:
        expected_types = [expected] if isinstance(expected, str) else expected
        if not any(_type_matches(instance, item) for item in expected_types):
            errors.append({"code": "json-schema-type", "message": f"Expected type {expected_types!r}.", "path": path})
            return errors

    if isinstance(instance, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                errors.append({"code": "json-schema-required", "message": f"Required property '{key}' is missing.", "path": f"{path}.{key}"})
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, value in instance.items():
            child_path = f"{path}.{key}"
            if key in properties:
                errors.extend(validate_instance(value, properties[key], root_schema=root_schema, path=child_path, _ref_stack=_ref_stack))
            elif additional is False:
                errors.append({"code": "json-schema-additional-property", "message": f"Unexpected property '{key}'.", "path": child_path})
            elif isinstance(additional, dict):
                errors.extend(validate_instance(value, additional, root_schema=root_schema, path=child_path, _ref_stack=_ref_stack))
        minimum_properties = schema.get("minProperties")
        if isinstance(minimum_properties, int) and len(instance) < minimum_properties:
            errors.append({"code": "json-schema-min-properties", "message": f"Object requires at least {minimum_properties} properties.", "path": path})

    if isinstance(instance, list):
        minimum_items = schema.get("minItems")
        if isinstance(minimum_items, int) and len(instance) < minimum_items:
            errors.append({"code": "json-schema-min-items", "message": f"Array requires at least {minimum_items} items.", "path": path})
        if schema.get("uniqueItems"):
            normalized = [json.dumps(item, sort_keys=True, ensure_ascii=False) for item in instance]
            if len(normalized) != len(set(normalized)):
                errors.append({"code": "json-schema-unique-items", "message": "Array items must be unique.", "path": path})
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, value in enumerate(instance):
                errors.extend(validate_instance(value, item_schema, root_schema=root_schema, path=f"{path}[{index}]", _ref_stack=_ref_stack))

    if isinstance(instance, str):
        minimum_length = schema.get("minLength")
        maximum_length = schema.get("maxLength")
        if isinstance(minimum_length, int) and len(instance) < minimum_length:
            errors.append({"code": "json-schema-min-length", "message": f"String must contain at least {minimum_length} characters.", "path": path})
        if isinstance(maximum_length, int) and len(instance) > maximum_length:
            errors.append({"code": "json-schema-max-length", "message": f"String must contain at most {maximum_length} characters.", "path": path})
        if "pattern" in schema:
            try:
                matched = re.fullmatch(schema["pattern"], instance)
            except (re.error, TypeError):
                errors.append({"code": "json-schema-pattern-definition", "message": "Schema contains an invalid pattern.", "path": path})
            else:
                if matched is None:
                    errors.append({"code": "json-schema-pattern", "message": "String does not match the required pattern.", "path": path})
        if "format" in schema and not _valid_format(instance, schema["format"]):
            errors.append({"code": "json-schema-format", "message": f"String is not a valid {schema['format']}.", "path": path})

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append({"code": "json-schema-minimum", "message": f"Number must be at least {schema['minimum']}.", "path": path})
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append({"code": "json-schema-maximum", "message": f"Number must be at most {schema['maximum']}.", "path": path})

    for keyword, requirement in (("anyOf", 1), ("oneOf", 1)):
        if keyword in schema:
            matches = sum(
                not validate_instance(instance, candidate, root_schema=root_schema, path=path, _ref_stack=_ref_stack)
                for candidate in schema[keyword]
            )
            valid = matches >= requirement if keyword == "anyOf" else matches == requirement
            if not valid:
                errors.append({"code": f"json-schema-{keyword}", "message": f"Value does not satisfy {keyword}.", "path": path})
    if "not" in schema and not validate_instance(instance, schema["not"], root_schema=root_schema, path=path, _ref_stack=_ref_stack):
        errors.append({"code": "json-schema-not", "message": "Value matches a prohibited schema.", "path": path})
    return errors
