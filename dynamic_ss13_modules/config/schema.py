from __future__ import annotations

from typing import Any

from dynamic_ss13_modules.errors import ValidationError


def validate_config_schema(instance: Any, schema: dict[str, Any], prefix: str = "config") -> None:
    """Validate the small JSON Schema subset Dynamic Modules needs at build time."""
    schema_type = schema.get("type")
    if schema_type:
        _check_type(instance, schema_type, prefix)

    if schema_type == "object" or isinstance(instance, dict):
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            raise ValidationError(f"{prefix}: schema.properties must be an object")
        required = schema.get("required", [])
        if not isinstance(required, list):
            raise ValidationError(f"{prefix}: schema.required must be a list")
        for key in required:
            if key not in instance:
                raise ValidationError(f"{prefix}: missing required key {key}")
        for key, subschema in properties.items():
            if key in instance:
                if not isinstance(subschema, dict):
                    raise ValidationError(f"{prefix}.{key}: property schema must be an object")
                validate_config_schema(instance[key], subschema, f"{prefix}.{key}")

    if isinstance(instance, (int, float)):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None and instance < minimum:
            raise ValidationError(f"{prefix}: value {instance} is below minimum {minimum}")
        if maximum is not None and instance > maximum:
            raise ValidationError(f"{prefix}: value {instance} is above maximum {maximum}")


def _check_type(instance: Any, expected: str, prefix: str) -> None:
    checks = {
        "object": lambda value: isinstance(value, dict),
        "array": lambda value: isinstance(value, list),
        "string": lambda value: isinstance(value, str),
        "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
        "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": lambda value: isinstance(value, bool),
        "null": lambda value: value is None,
    }
    check = checks.get(expected)
    if check is None:
        raise ValidationError(f"{prefix}: unsupported schema type {expected}")
    if not check(instance):
        raise ValidationError(f"{prefix}: expected {expected}, got {type(instance).__name__}")

