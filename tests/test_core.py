"""Tests for toolsmith.core — registry, validation, execution, and auditing."""

import time

import pytest

from toolsmith import Tool, ToolRegistry, ToolResult, ToolStatus, tool, SchemaValidator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _adder(a: int, b: int) -> int:
    return a + b


@pytest.fixture
def registry() -> ToolRegistry:
    return ToolRegistry(audit=False)


@pytest.fixture
def adder_tool() -> Tool:
    return Tool(
        name="adder",
        description="Add two integers",
        fn=_adder,
        parameters_schema={
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"},
            },
            "required": ["a", "b"],
        },
    )


# ---------------------------------------------------------------------------
# Registration & discovery
# ---------------------------------------------------------------------------

class TestRegistration:
    def test_register_and_list(self, registry: ToolRegistry, adder_tool: Tool) -> None:
        registry.register(adder_tool)
        assert "adder" in registry.list_tools()
        assert registry.get("adder") is adder_tool

    def test_duplicate_register_raises(self, registry: ToolRegistry, adder_tool: Tool) -> None:
        registry.register(adder_tool)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(adder_tool)

    def test_unregister(self, registry: ToolRegistry, adder_tool: Tool) -> None:
        registry.register(adder_tool)
        registry.unregister("adder")
        assert "adder" not in registry.list_tools()


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

class TestExecution:
    def test_successful_execution(self, registry: ToolRegistry, adder_tool: Tool) -> None:
        registry.register(adder_tool)
        result = registry.execute("adder", {"a": 3, "b": 4})
        assert result.status == ToolStatus.SUCCESS
        assert result.output == 7

    def test_missing_param_returns_error(self, registry: ToolRegistry, adder_tool: Tool) -> None:
        registry.register(adder_tool)
        result = registry.execute("adder", {"a": 3})
        assert result.status == ToolStatus.ERROR
        assert "Missing required parameter" in (result.error or "")

    def test_execution_catches_exception(self, registry: ToolRegistry) -> None:
        def boom() -> None:
            raise RuntimeError("kaboom")

        t = Tool(name="boom", description="explodes", fn=boom)
        registry.register(t)
        result = registry.execute("boom")
        assert result.status == ToolStatus.ERROR
        assert "kaboom" in (result.error or "")


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

class TestDecorator:
    def test_tool_decorator_creates_tool(self) -> None:
        @tool(name="greet", description="Say hello")
        def greet(name: str) -> str:
            return f"Hello, {name}!"

        assert isinstance(greet, Tool)
        assert greet.name == "greet"
        assert greet.fn(name="World") == "Hello, World!"

    def test_inferred_schema(self) -> None:
        @tool(name="echo")
        def echo(message: str, count: int) -> str:
            return message * count

        schema = echo.parameters_schema
        assert "message" in schema["properties"]
        assert schema["properties"]["count"]["type"] == "integer"


# ---------------------------------------------------------------------------
# Schema validator
# ---------------------------------------------------------------------------

class TestSchemaValidator:
    def test_valid_input(self) -> None:
        schema = {
            "type": "object",
            "properties": {"x": {"type": "integer"}},
            "required": ["x"],
        }
        assert SchemaValidator.validate(schema, {"x": 42}) == []

    def test_wrong_type(self) -> None:
        schema = {
            "type": "object",
            "properties": {"x": {"type": "integer"}},
            "required": ["x"],
        }
        errors = SchemaValidator.validate(schema, {"x": "not_an_int"})
        assert len(errors) == 1
        assert "expected type" in errors[0]
