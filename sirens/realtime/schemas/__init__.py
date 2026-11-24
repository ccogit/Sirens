"""Validierung des bewusst begrenzten JSON-Schema-v1-Profils ohne Fremdmodule."""
import json
import math
import re
from pathlib import Path
from ..contracts import invalid

SCHEMAS = Path(__file__).parent
TYPES = {"object": lambda v: isinstance(v, dict),
         "array": lambda v: isinstance(v, list),
         "string": lambda v: isinstance(v, str),
         "integer": lambda v: type(v) is int,
         "number": lambda v: type(v) in (int, float) and -2**53 <= v <= 2**53 and math.isfinite(v),
         "boolean": lambda v: type(v) is bool,
         "null": lambda v: v is None}
KEYWORDS = {"$schema", "title", "type", "enum", "oneOf", "anyOf", "properties",
            "required", "additionalProperties", "items", "minItems", "maxItems",
            "minLength", "maxLength", "pattern", "minimum", "maximum"}

def matches(schema, value):
    if set(schema) - KEYWORDS:
        raise ValueError("Unbekanntes Schema-Schlüsselwort")
    if "oneOf" in schema and sum(matches(s, value) for s in schema["oneOf"]) != 1:
        return False
    if "anyOf" in schema and not any(matches(s, value) for s in schema["anyOf"]):
        return False
    if "type" in schema and not TYPES[schema["type"]](value):
        return False
    if "enum" in schema and not any(type(value) is type(v) and value == v for v in schema["enum"]):
        return False
    if isinstance(value, dict):
        props = schema.get("properties", {})
        if not set(schema.get("required", ())) <= value.keys():
            return False
        if schema.get("additionalProperties") is False and value.keys() - props.keys():
            return False
        if not all(matches(props[k], v) for k, v in value.items() if k in props):
            return False
    if isinstance(value, list):
        if not schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", len(value)):
            return False
        if "items" in schema and not all(matches(schema["items"], v) for v in value):
            return False
    if isinstance(value, str):
        if not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", len(value)):
            return False
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            return False
    if type(value) in (int, float):
        if not schema.get("minimum", -float("inf")) <= value <= schema.get("maximum", float("inf")):
            return False
    return True

def validate(name, value):
    if not re.fullmatch(r"[a-z_]+", name):
        raise invalid("schema")
    schema = json.loads((SCHEMAS / (name + ".schema.json")).read_text(encoding="utf-8"))
    if not matches(schema, value):
        raise invalid(name)
    return value
