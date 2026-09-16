"""Bounded, dependency-free evaluator for ReportKit's JSON Schema subset.

This is not a general JSON Schema implementation. Unknown keywords, recursive or
external references, and unsupported regex syntax fail definition validation.
Patterns use full-string matching, as in the original ReportKit contracts.
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from functools import lru_cache
from typing import Any

MAX_SCHEMA_DEPTH = 20
MAX_SCHEMA_NODES = 500
MAX_SCHEMA_VALUES = 10000
MAX_SCHEMA_EXPANSION = 10000
MAX_INSTANCE_DEPTH = 64
MAX_VALIDATION_STEPS = 200000
MAX_PATTERN_LENGTH = 128
MAX_PATTERN_REPEAT = 1024
MAX_PATTERN_STEPS = 1000000
MAX_STRING_LENGTH = 1024 * 1024
ALLOWED_SCHEMA_KEYWORDS = {
    "$schema", "$id", "$defs", "$ref", "title", "description", "default",
    "type", "const", "enum", "properties", "additionalProperties", "required",
    "minProperties", "maxProperties", "items", "minItems", "maxItems",
    "uniqueItems", "minLength", "maxLength", "pattern", "format",
    "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
    "anyOf", "oneOf", "allOf", "not",
}
ALLOWED_TYPES = {"object", "array", "string", "boolean", "integer", "number", "null"}
ALLOWED_FORMATS = {"date", "date-time"}
COUNT_KEYWORDS = (
    "minProperties", "maxProperties", "minItems", "maxItems", "minLength", "maxLength",
)
NUMBER_KEYWORDS = ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum")
COMBINATORS = ("anyOf", "oneOf", "allOf")
# This fixed, unambiguous expression is used by the checked-in capability schema.
# It is the only grouped expression supported; arbitrary groups remain forbidden.
VERSION_PATTERN = r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"


def _issue(code: str, message: str, path: str) -> dict[str, str]:
    return {"code": code, "message": message, "path": path}


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


def _json_shape(value: Any, *, max_depth: int, max_nodes: int) -> str | None:
    pending = [(value, 0)]
    nodes = 0
    while pending:
        current, depth = pending.pop()
        nodes += 1
        if nodes > max_nodes or depth > max_depth:
            return "JSON value exceeds the supported size or nesting budget."
        if isinstance(current, dict):
            if not all(isinstance(key, str) for key in current):
                return "JSON object keys must be strings."
            if len(current) + len(pending) > max_nodes:
                return "JSON value exceeds the supported size budget."
            pending.extend((child, depth + 1) for child in current.values())
        elif isinstance(current, list):
            if len(current) + len(pending) > max_nodes:
                return "JSON value exceeds the supported size budget."
            pending.extend((child, depth + 1) for child in current)
        elif isinstance(current, float):
            if not math.isfinite(current):
                return "JSON numbers must be finite."
        elif isinstance(current, str):
            if len(current) > MAX_STRING_LENGTH:
                return f"JSON strings cannot exceed {MAX_STRING_LENGTH} characters."
        elif current is not None and not isinstance(current, (str, bool, int)):
            return "Schema and instance values must be JSON values."
    return None


def _identity(value: Any, budget: _Budget | None = None) -> Any:
    """JSON equality distinguishes booleans from numbers, but not 1 from 1.0."""
    if budget is not None:
        budget.charge()
    if isinstance(value, dict):
        return ("object", tuple(sorted((key, _identity(child, budget)) for key, child in value.items())))
    if isinstance(value, list):
        return ("array", tuple(_identity(child, budget) for child in value))
    if isinstance(value, bool):
        return ("boolean", value)
    if isinstance(value, (int, float)):
        return ("number", value)
    return (type(value).__name__, value)


def _resolve(root: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise ValueError("Only local JSON Pointer references are supported.")
    current: Any = root
    for segment in reference[2:].split("/"):
        if re.search(r"~(?![01])", segment):
            raise ValueError("Invalid JSON Pointer escape.")
        segment = segment.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and segment in current:
            current = current[segment]
        elif isinstance(current, list) and re.fullmatch(r"0|[1-9][0-9]*", segment):
            # Avoid converting an attacker-controlled, arbitrarily large index.
            if len(segment) > 6 or int(segment) >= len(current):
                raise ValueError("Schema reference array index is out of range.")
            current = current[int(segment)]
        else:
            raise ValueError("Schema reference target does not exist.")
    if not isinstance(current, dict):
        raise ValueError("Schema reference must resolve to a schema object.")
    return current


@lru_cache(maxsize=256)
def _pattern_atoms(pattern: str) -> tuple[tuple[re.Pattern[str], int, int | None], ...]:
    """Parse flat regex atoms for linear dynamic-programming matching.

    Each atom consumes exactly one character. Assertions, groups, alternation,
    backreferences, and repeated quantifiers are deliberately unsupported.
    """
    if len(pattern) > MAX_PATTERN_LENGTH:
        raise ValueError(f"pattern must be at most {MAX_PATTERN_LENGTH} characters.")
    atoms = []
    index = 1 if pattern.startswith("^") else 0
    end = len(pattern)
    while index < end:
        if pattern[index] == "$" and index == end - 1:
            break
        start = index
        char = pattern[index]
        if char == "[":
            index += 1
            if index < end and pattern[index] == "^":
                index += 1
            if index < end and pattern[index] == "]":
                index += 1
            while index < end and pattern[index] != "]":
                index += 2 if pattern[index] == "\\" else 1
            if index >= end:
                raise ValueError("Unterminated pattern character class.")
            index += 1
        elif char == "\\":
            index += 1
            if index >= end:
                raise ValueError("Incomplete pattern escape.")
            escaped = pattern[index]
            if escaped.isdigit() or escaped in "AbBZGN":
                raise ValueError("Pattern assertions and backreferences are not supported.")
            index += {"x": 3, "u": 5, "U": 9}.get(escaped, 1)
        elif char in "()|^$*+?{}":
            raise ValueError("Pattern groups, alternation, assertions, and repeated quantifiers are not supported.")
        else:
            index += 1
        source = pattern[start:index]
        try:
            atom = re.compile(source)
        except (re.error, OverflowError) as exception:
            raise ValueError(f"Invalid regular expression: {exception}") from exception
        minimum, maximum = 1, 1
        if index < end and pattern[index] in "*+?":
            quantifier = pattern[index]
            minimum = 1 if quantifier == "+" else 0
            maximum = 1 if quantifier == "?" else None
            index += 1
        elif index < end and pattern[index] == "{":
            match = re.match(r"\{([0-9]+)(?:,([0-9]*))?\}", pattern[index:])
            if match is None:
                raise ValueError("Invalid pattern repetition.")
            bounds = [part for part in match.groups() if part]
            if any(len(part) > 4 or int(part) > MAX_PATTERN_REPEAT for part in bounds):
                raise ValueError(f"Pattern repetition cannot exceed {MAX_PATTERN_REPEAT}.")
            minimum = int(match[1])
            maximum = minimum if match[2] is None else int(match[2]) if match[2] else None
            if maximum is not None and minimum > maximum:
                raise ValueError("Pattern repetition minimum exceeds its maximum.")
            index += len(match[0])
        atoms.append((atom, minimum, maximum))
    return tuple(atoms)


def _check_pattern(pattern: Any) -> str | None:
    if not isinstance(pattern, str):
        return "pattern must be a string."
    if pattern == VERSION_PATTERN:
        return None
    try:
        _pattern_atoms(pattern)
    except ValueError as exception:
        return str(exception)
    return None


def validate_schema_definition(schema: Any) -> list[dict[str, str]]:
    """Validate every node before evaluation; return structured definition errors."""
    problem = _json_shape(schema, max_depth=MAX_SCHEMA_DEPTH * 3, max_nodes=MAX_SCHEMA_VALUES)
    if problem:
        return [_issue("json-schema-definition", problem, "$")]
    errors: list[dict[str, str]] = []
    pending = [(schema, "$", 0)]
    nodes: dict[int, tuple[dict[str, Any], str]] = {}
    edges: dict[int, list[int]] = {}

    def add(code: str, text: str, path: str) -> None:
        errors.append(_issue(code, text, path))

    while pending:
        value, path, depth = pending.pop()
        if len(nodes) + len(pending) >= MAX_SCHEMA_NODES:
            add("json-schema-too-large", f"Schema exceeds {MAX_SCHEMA_NODES} nodes.", path)
            break
        if depth > MAX_SCHEMA_DEPTH:
            add("json-schema-too-deep", f"Schema exceeds depth {MAX_SCHEMA_DEPTH}.", path)
            continue
        if not isinstance(value, dict):
            add("json-schema-definition", "Every schema node must be an object.", path)
            continue
        node_id = id(value)
        nodes[node_id] = (value, path)
        edges[node_id] = []

        def child(candidate: Any, child_path: str) -> None:
            pending.append((candidate, child_path, depth + 1))
            if isinstance(candidate, dict):
                edges[node_id].append(id(candidate))

        for keyword in sorted(set(value) - ALLOWED_SCHEMA_KEYWORDS):
            add("json-schema-keyword", f"Unsupported schema keyword '{keyword}'.", f"{path}.{keyword}")
        for keyword in ("$schema", "$id", "title", "description"):
            if keyword in value and not isinstance(value[keyword], str):
                add("json-schema-definition", f"{keyword} must be a string.", f"{path}.{keyword}")
        if "type" in value:
            expected = value["type"]
            types = [expected] if isinstance(expected, str) else expected
            if (
                not isinstance(types, list) or not types
                or any(not isinstance(item, str) or item not in ALLOWED_TYPES for item in types)
                or len(set(types)) != len(types)
            ):
                add("json-schema-definition", "type must contain distinct supported JSON types.", f"{path}.type")
        if "required" in value:
            required = value["required"]
            if (
                not isinstance(required, list)
                or any(not isinstance(item, str) for item in required)
                or len(set(required)) != len(required)
            ):
                add("json-schema-definition", "required must be an array of distinct strings.", f"{path}.required")
        if "enum" in value:
            choices = value["enum"]
            if not isinstance(choices, list) or not choices:
                add("json-schema-definition", "enum must be a non-empty array of JSON values.", f"{path}.enum")
            elif len({_identity(item) for item in choices}) != len(choices):
                add("json-schema-definition", "enum values must be distinct.", f"{path}.enum")
        for keyword in COUNT_KEYWORDS:
            if keyword in value and (type(value[keyword]) is not int or value[keyword] < 0):
                add("json-schema-definition", f"{keyword} must be a non-negative integer.", f"{path}.{keyword}")
        for keyword in NUMBER_KEYWORDS:
            if keyword in value and not _type_matches(value[keyword], "number"):
                add("json-schema-definition", f"{keyword} must be a finite number.", f"{path}.{keyword}")
        if "uniqueItems" in value and not isinstance(value["uniqueItems"], bool):
            add("json-schema-definition", "uniqueItems must be a boolean.", f"{path}.uniqueItems")
        if "pattern" in value:
            problem = _check_pattern(value["pattern"])
            if problem:
                add("json-schema-pattern-definition", problem, f"{path}.pattern")
        if "format" in value and (
            not isinstance(value["format"], str) or value["format"] not in ALLOWED_FORMATS
        ):
            add("json-schema-format-definition", "format must be date or date-time.", f"{path}.format")
        for keyword in ("properties", "$defs"):
            if keyword in value:
                children = value[keyword]
                if not isinstance(children, dict):
                    add("json-schema-definition", f"{keyword} must be an object.", f"{path}.{keyword}")
                else:
                    for name, candidate in children.items():
                        child(candidate, f"{path}.{keyword}.{name}")
        if "additionalProperties" in value and not isinstance(value["additionalProperties"], bool):
            child(value["additionalProperties"], f"{path}.additionalProperties")
        for keyword in ("items", "not"):
            if keyword in value:
                child(value[keyword], f"{path}.{keyword}")
        for keyword in COMBINATORS:
            if keyword in value:
                candidates = value[keyword]
                if not isinstance(candidates, list) or not candidates:
                    add("json-schema-definition", f"{keyword} must be a non-empty array.", f"{path}.{keyword}")
                else:
                    for index, candidate in enumerate(candidates):
                        child(candidate, f"{path}.{keyword}[{index}]")

    # Only resolve references into actual schema positions, never annotation data.
    for node_id, (value, path) in nodes.items():
        if "$ref" not in value:
            continue
        reference = value["$ref"]
        if not isinstance(reference, str):
            add("json-schema-ref", "$ref must be a local JSON Pointer string.", f"{path}.$ref")
            continue
        try:
            target = _resolve(schema, reference)
        except ValueError as exception:
            add("json-schema-ref", str(exception), f"{path}.$ref")
            continue
        if id(target) not in nodes:
            add("json-schema-ref", "Reference must target a supported schema position.", f"{path}.$ref")
        else:
            edges[node_id].append(id(target))
    if errors:
        return errors

    # Memoized graph traversal prevents exponential reference expansion during
    # definition checking. Reject expensive DAGs before evaluating any instance.
    visiting: set[int] = set()
    costs: dict[int, int] = {}
    heights: dict[int, int] = {}
    stack = [(id(schema), False)]
    while stack:
        node_id, finishing = stack.pop()
        if node_id in costs:
            continue
        if finishing:
            visiting.remove(node_id)
            costs[node_id] = 1 + sum(costs[target] for target in edges[node_id])
            heights[node_id] = 1 + max((heights[target] for target in edges[node_id]), default=0)
            if costs[node_id] > MAX_SCHEMA_EXPANSION:
                return [_issue("json-schema-too-large", "Schema reference expansion exceeds the evaluation budget.", nodes[node_id][1])]
            if heights[node_id] > MAX_SCHEMA_DEPTH + 1:
                return [_issue("json-schema-too-deep", "Expanded schema exceeds the depth budget.", nodes[node_id][1])]
        elif node_id in visiting:
            return [_issue("json-schema-recursive-ref", "Recursive schema references are not supported.", nodes[node_id][1])]
        else:
            visiting.add(node_id)
            stack.append((node_id, True))
            stack.extend((target, False) for target in edges[node_id] if target not in costs)
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


class _EvaluationLimit(Exception):
    pass


class _Budget:
    def __init__(self) -> None:
        self.steps = MAX_VALIDATION_STEPS
        self.pattern_steps = MAX_PATTERN_STEPS

    def charge(self, steps: int = 1, *, pattern: bool = False) -> None:
        if pattern:
            self.pattern_steps -= steps
        else:
            self.steps -= steps
        if self.steps < 0 or self.pattern_steps < 0:
            raise _EvaluationLimit


def _pattern_matches(pattern: str, value: str, budget: _Budget) -> bool:
    if pattern == VERSION_PATTERN:
        budget.charge(len(value), pattern=True)
        return re.fullmatch(pattern, value) is not None
    atoms = _pattern_atoms(pattern)
    budget.charge(max(1, len(atoms)) * (len(value) + 1), pattern=True)
    reachable = [True] + [False] * len(value)
    for atom, minimum, maximum in atoms:
        prefix = [0]
        for possible in reachable:
            prefix.append(prefix[-1] + possible)
        following = [False] * len(reachable)
        run = 0
        for end in range(len(reachable)):
            if end:
                run = run + 1 if atom.fullmatch(value[end - 1]) else 0
            if run >= minimum:
                lower = end - (min(run, maximum) if maximum is not None else run)
                upper = end - minimum
                following[end] = prefix[upper + 1] > prefix[lower]
        reachable = following
    return reachable[-1]


def validate_instance(
    instance: Any,
    schema: dict[str, Any],
    *,
    root_schema: dict[str, Any] | None = None,
    path: str = "$",
    _ref_stack: tuple[str, ...] = (),
) -> list[dict[str, str]]:
    """Validate definitions first, then evaluate with a shared, fail-closed budget."""
    root = schema if root_schema is None else root_schema
    errors = validate_schema_definition(root)
    if errors:
        return errors
    if root is not schema:
        # Public callers may select a subschema, but not inject an unchecked node.
        pending = [root]
        found = False
        while pending:
            current = pending.pop()
            if current is schema:
                found = True
                break
            for keyword in ("properties", "$defs"):
                pending.extend(current.get(keyword, {}).values())
            for keyword in ("items", "not", "additionalProperties"):
                if isinstance(current.get(keyword), dict):
                    pending.append(current[keyword])
            for keyword in COMBINATORS:
                pending.extend(current.get(keyword, []))
        if not found:
            return [_issue("json-schema-definition", "schema must be a schema position in root_schema.", path)]
    problem = _json_shape(instance, max_depth=MAX_INSTANCE_DEPTH, max_nodes=MAX_VALIDATION_STEPS)
    if problem:
        return [_issue("json-schema-instance", problem, path)]
    try:
        return _validate(instance, schema, root, path, _Budget())
    except _EvaluationLimit:
        return [_issue("json-schema-budget", "Schema evaluation exceeds the supported work budget.", path)]


def _validate(instance: Any, schema: dict[str, Any], root: dict[str, Any], path: str, budget: _Budget) -> list[dict[str, str]]:
    budget.charge()
    errors: list[dict[str, str]] = []

    def add(code: str, text: str, at: str = path) -> None:
        errors.append(_issue(code, text, at))

    if "$ref" in schema:
        errors.extend(_validate(instance, _resolve(root, schema["$ref"]), root, path, budget))
    if "const" in schema and _identity(instance, budget) != _identity(schema["const"], budget):
        add("json-schema-const", f"Value must equal {schema['const']!r}.")
    if "enum" in schema:
        budget.charge(len(schema["enum"]))
        if _identity(instance, budget) not in {_identity(choice, budget) for choice in schema["enum"]}:
            add("json-schema-enum", f"Value is not one of {schema['enum']!r}.")
    if "type" in schema:
        expected = schema["type"]
        types = [expected] if isinstance(expected, str) else expected
        if not any(_type_matches(instance, item) for item in types):
            add("json-schema-type", f"Expected type {types!r}.")
            return errors
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            budget.charge()
            if key not in instance:
                add("json-schema-required", f"Required property '{key}' is missing.", f"{path}.{key}")
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, value in instance.items():
            budget.charge()
            if key in properties:
                errors.extend(_validate(value, properties[key], root, f"{path}.{key}", budget))
            elif additional is False:
                add("json-schema-additional-property", f"Unexpected property '{key}'.", f"{path}.{key}")
            elif isinstance(additional, dict):
                errors.extend(_validate(value, additional, root, f"{path}.{key}", budget))
        if "minProperties" in schema and len(instance) < schema["minProperties"]:
            add("json-schema-min-properties", f"Object requires at least {schema['minProperties']} properties.")
        if "maxProperties" in schema and len(instance) > schema["maxProperties"]:
            add("json-schema-max-properties", f"Object permits at most {schema['maxProperties']} properties.")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            add("json-schema-min-items", f"Array requires at least {schema['minItems']} items.")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            add("json-schema-max-items", f"Array permits at most {schema['maxItems']} items.")
        if schema.get("uniqueItems"):
            budget.charge(len(instance))
            if len({_identity(item, budget) for item in instance}) != len(instance):
                add("json-schema-unique-items", "Array items must be unique.")
        if "items" in schema:
            for index, value in enumerate(instance):
                errors.extend(_validate(value, schema["items"], root, f"{path}[{index}]", budget))
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            add("json-schema-min-length", f"String must contain at least {schema['minLength']} characters.")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            add("json-schema-max-length", f"String must contain at most {schema['maxLength']} characters.")
        if "pattern" in schema and not _pattern_matches(schema["pattern"], instance, budget):
            add("json-schema-pattern", "String does not match the required pattern.")
        if "format" in schema and not _valid_format(instance, schema["format"]):
            add("json-schema-format", f"String is not a valid {schema['format']}.")
    if _type_matches(instance, "number"):
        comparisons = (
            ("minimum", lambda bound: instance < bound, "at least"),
            ("maximum", lambda bound: instance > bound, "at most"),
            ("exclusiveMinimum", lambda bound: instance <= bound, "greater than"),
            ("exclusiveMaximum", lambda bound: instance >= bound, "less than"),
        )
        for keyword, comparison, description in comparisons:
            if keyword in schema and comparison(schema[keyword]):
                add(f"json-schema-{keyword}", f"Number must be {description} {schema[keyword]}.")
    for keyword in COMBINATORS:
        if keyword in schema:
            matches = sum(not _validate(instance, candidate, root, path, budget) for candidate in schema[keyword])
            valid = matches >= 1 if keyword == "anyOf" else matches == 1 if keyword == "oneOf" else matches == len(schema[keyword])
            if not valid:
                add(f"json-schema-{keyword}", f"Value does not satisfy {keyword}.")
    if "not" in schema and not _validate(instance, schema["not"], root, path, budget):
        add("json-schema-not", "Value matches a prohibited schema.")
    return errors
