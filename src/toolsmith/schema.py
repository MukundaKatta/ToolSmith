"""Tool-schema generation from Python callables.

When an agent registers a new tool at runtime, we need a JSON-Schema
description that an LLM's function-calling API can consume. This
module introspects signatures/docstrings/type hints and produces that
schema — with validation going the other way too.
"""

from __future__ import annotations

import inspect
import re
from dataclasses import dataclass
from typing import Any, Callable, Literal, Union, get_args, get_origin, get_type_hints


JsonType = Literal["string", "integer", "number", "boolean", "array", "object", "null"]


@dataclass
class ToolSchema:
    name: str
    description: str
    parameters: dict  # JSON Schema
    required: list[str]

    def as_openai(self) -> dict:
        """OpenAI function-calling tool spec."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required,
                    "additionalProperties": False,
                },
            },
        }

    def as_anthropic(self) -> dict:
        """Anthropic tool_use spec."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": self.required,
            },
        }


_PRIMITIVES: dict[type, JsonType] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


def _type_to_schema(tp: Any) -> dict:
    origin = get_origin(tp)
    args = get_args(tp)

    if tp in _PRIMITIVES:
        return {"type": _PRIMITIVES[tp]}
    if tp is type(None):
        return {"type": "null"}

    # Optional[X] / Union[X, None]
    if origin is Union:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            inner = _type_to_schema(non_none[0])
            # Allow null to signal optionality.
            return {"anyOf": [inner, {"type": "null"}]}
        return {"anyOf": [_type_to_schema(a) for a in args]}

    if origin in (list, tuple, set, frozenset):
        item = args[0] if args else str
        return {"type": "array", "items": _type_to_schema(item)}

    if origin is dict:
        val_tp = args[1] if len(args) == 2 else Any
        return {
            "type": "object",
            "additionalProperties": _type_to_schema(val_tp) if val_tp is not Any else True,
        }

    if origin is Literal:
        return {"enum": list(args)}

    # Fallback: treat as opaque string
    return {"type": "string"}


def schema_from(fn: Callable[..., Any], *, name: str | None = None) -> ToolSchema:
    """Build a ToolSchema from a Python callable's signature + docstring."""
    sig = inspect.signature(fn)
    try:
        hints = get_type_hints(fn)
    except Exception:
        hints = {}

    doc = inspect.getdoc(fn) or ""
    description, param_docs = _parse_docstring(doc)

    properties: dict[str, dict] = {}
    required: list[str] = []

    for pname, param in sig.parameters.items():
        if pname in ("self", "cls"):
            continue
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        schema = _type_to_schema(hints.get(pname, str))
        if pname in param_docs:
            schema["description"] = param_docs[pname]
        if param.default is inspect.Parameter.empty:
            required.append(pname)
        else:
            schema["default"] = param.default if _is_jsonable(param.default) else repr(param.default)
        properties[pname] = schema

    return ToolSchema(
        name=name or fn.__name__,
        description=description.strip() or fn.__name__,
        parameters=properties,
        required=required,
    )


def validate_args(schema: ToolSchema, args: dict[str, Any]) -> list[str]:
    """Return a list of validation errors against the tool's schema."""
    errors: list[str] = []
    for req in schema.required:
        if req not in args:
            errors.append(f"missing required argument: {req}")
    for k, v in args.items():
        if k not in schema.parameters:
            errors.append(f"unknown argument: {k}")
            continue
        expected = schema.parameters[k].get("type")
        if expected and not _matches_type(v, expected):
            errors.append(f"argument {k!r} expected {expected}, got {type(v).__name__}")
    return errors


def _matches_type(v: Any, expected: str) -> bool:
    return {
        "string": isinstance(v, str),
        "integer": isinstance(v, int) and not isinstance(v, bool),
        "number": isinstance(v, (int, float)) and not isinstance(v, bool),
        "boolean": isinstance(v, bool),
        "array": isinstance(v, list),
        "object": isinstance(v, dict),
        "null": v is None,
    }.get(expected, True)


_PARAM_RE = re.compile(r"^\s*(?::param\s+|Args?:\s*\n\s*)?(\w+)\s*[:\-]\s*(.+)$")


def _parse_docstring(doc: str) -> tuple[str, dict[str, str]]:
    """Separate a description paragraph from `param: description` lines."""
    if not doc:
        return "", {}
    lines = doc.splitlines()
    desc: list[str] = []
    params: dict[str, str] = {}
    in_args = False
    for line in lines:
        stripped = line.strip()
        if stripped.lower() in ("args:", "arguments:", "parameters:"):
            in_args = True
            continue
        if in_args:
            m = _PARAM_RE.match(line)
            if m:
                params[m.group(1)] = m.group(2).strip()
                continue
            if not stripped:
                in_args = False
                continue
        if not in_args:
            desc.append(line)
    return "\n".join(desc).strip(), params


def _is_jsonable(v: Any) -> bool:
    return isinstance(v, (str, int, float, bool, list, dict, tuple)) or v is None
