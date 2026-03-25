"""Core module: Tool definitions, registry, validation, sandboxing, and audit logging."""

from __future__ import annotations

import datetime
import json
import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from toolsmith.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class ToolStatus(Enum):
    """Possible outcomes of a tool execution."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class ToolResult:
    """Encapsulates the result of a single tool invocation."""
    status: ToolStatus
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
        }


@dataclass
class Tool:
    """Runtime representation of a registered tool."""
    name: str
    description: str
    fn: Callable[..., Any]
    parameters_schema: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def to_openai_schema(self) -> dict[str, Any]:
        """Export the tool definition in OpenAI function-calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

def tool(
    name: str,
    description: str = "",
    parameters_schema: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> Callable[[Callable[..., Any]], Tool]:
    """Decorator that wraps a plain function into a :class:`Tool` instance."""

    def decorator(fn: Callable[..., Any]) -> Tool:
        schema = parameters_schema or _infer_schema(fn)
        return Tool(
            name=name,
            description=description or fn.__doc__ or "",
            fn=fn,
            parameters_schema=schema,
            tags=tags or [],
        )

    return decorator


def _infer_schema(fn: Callable[..., Any]) -> dict[str, Any]:
    """Build a minimal JSON-Schema ``object`` from function annotations."""
    hints = getattr(fn, "__annotations__", {})
    type_map = {str: "string", int: "integer", float: "number", bool: "boolean"}
    properties: dict[str, Any] = {}
    for param, hint in hints.items():
        if param == "return":
            continue
        properties[param] = {"type": type_map.get(hint, "string")}
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties.keys()),
    }


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

class SchemaValidator:
    """Lightweight JSON-Schema validator (supports type + required checks)."""

    @staticmethod
    def validate(schema: dict[str, Any], data: dict[str, Any]) -> list[str]:
        """Return a list of validation error strings (empty means valid)."""
        errors: list[str] = []
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        for req in required:
            if req not in data:
                errors.append(f"Missing required parameter: '{req}'")

        json_to_python = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
        }
        for key, value in data.items():
            if key not in properties:
                continue
            expected_type = properties[key].get("type")
            if expected_type and not isinstance(value, json_to_python.get(expected_type, object)):
                errors.append(
                    f"Parameter '{key}' expected type '{expected_type}', got '{type(value).__name__}'"
                )

        return errors


# ---------------------------------------------------------------------------
# Sandbox executor
# ---------------------------------------------------------------------------

class SandboxExecutor:
    """Execute a callable with a wall-clock timeout."""

    def __init__(self, timeout: int | None = None) -> None:
        self.timeout = timeout or settings.sandbox_timeout

    def run(self, fn: Callable[..., Any], kwargs: dict[str, Any]) -> ToolResult:
        result_holder: dict[str, Any] = {}
        error_holder: dict[str, Any] = {}

        def _target() -> None:
            try:
                result_holder["value"] = fn(**kwargs)
            except Exception as exc:
                error_holder["value"] = str(exc)

        start = _now_ms()
        thread = threading.Thread(target=_target, daemon=True)
        thread.start()
        thread.join(timeout=self.timeout)

        duration = _now_ms() - start

        if thread.is_alive():
            return ToolResult(status=ToolStatus.TIMEOUT, duration_ms=duration,
                              error=f"Timed out after {self.timeout}s")

        if "value" in error_holder:
            return ToolResult(status=ToolStatus.ERROR, error=error_holder["value"],
                              duration_ms=duration)

        return ToolResult(status=ToolStatus.SUCCESS, output=result_holder.get("value"),
                          duration_ms=duration)


# ---------------------------------------------------------------------------
# Audit logger
# ---------------------------------------------------------------------------

class AuditLogger:
    """Append-only JSONL audit log for every tool invocation."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or settings.audit_log_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: list[dict[str, Any]] = []

    def log(self, tool_name: str, inputs: dict[str, Any], result: ToolResult) -> None:
        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "tool": tool_name,
            "inputs": inputs,
            "result": result.to_dict(),
        }
        self._entries.append(entry)
        try:
            with self.path.open("a") as fh:
                fh.write(json.dumps(entry) + "\n")
        except OSError:
            logger.warning("Failed to write audit log to %s", self.path)

    @property
    def entries(self) -> list[dict[str, Any]]:
        return list(self._entries)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class ToolRegistry:
    """Central registry for discovering, validating, and executing tools."""

    def __init__(self, *, audit: bool = True, sandbox_timeout: int | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        self._validator = SchemaValidator()
        self._sandbox = SandboxExecutor(timeout=sandbox_timeout)
        self._audit = AuditLogger() if audit else None

    # -- registration -------------------------------------------------------

    def register(self, tool_obj: Tool) -> None:
        """Register a :class:`Tool` instance."""
        if not isinstance(tool_obj, Tool):
            raise TypeError(f"Expected a Tool instance, got {type(tool_obj).__name__}")
        if tool_obj.name in self._tools:
            raise ValueError(f"Tool '{tool_obj.name}' is already registered")
        self._tools[tool_obj.name] = tool_obj
        logger.info("Registered tool: %s", tool_obj.name)

    def unregister(self, name: str) -> None:
        """Remove a tool by name."""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found")
        del self._tools[name]

    # -- discovery ----------------------------------------------------------

    def get(self, name: str) -> Tool:
        """Retrieve a tool by name, raising KeyError if missing."""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found in registry")
        return self._tools[name]

    def list_tools(self) -> list[str]:
        """Return sorted list of registered tool names."""
        return sorted(self._tools.keys())

    def search(self, tag: str) -> list[Tool]:
        """Return tools that carry the given tag."""
        return [t for t in self._tools.values() if tag in t.tags]

    # -- execution ----------------------------------------------------------

    def execute(self, name: str, inputs: dict[str, Any] | None = None) -> ToolResult:
        """Validate inputs then execute a tool inside the sandbox."""
        inputs = inputs or {}
        t = self.get(name)

        errors = self._validator.validate(t.parameters_schema, inputs)
        if errors:
            result = ToolResult(status=ToolStatus.ERROR, error="; ".join(errors))
        else:
            result = self._sandbox.run(t.fn, inputs)

        if self._audit:
            self._audit.log(name, inputs, result)

        return result

    def export_schemas(self) -> list[dict[str, Any]]:
        """Export all tools in OpenAI function-calling format."""
        return [t.to_openai_schema() for t in self._tools.values()]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_ms() -> float:
    """Current time in milliseconds."""
    return datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000
