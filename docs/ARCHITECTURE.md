# Architecture

## Overview

ToolSmith follows a layered architecture designed for extensibility and safety.

```
┌──────────────────────────────────────┐
│           ToolRegistry               │  Public API
├──────────────────────────────────────┤
│  SchemaValidator  │ SandboxExecutor  │  Middleware
├──────────────────────────────────────┤
│           AuditLogger                │  Observability
├──────────────────────────────────────┤
│        Tool / ToolResult             │  Data Model
└──────────────────────────────────────┘
```

## Components

### Tool (dataclass)
Represents a callable tool with metadata: `name`, `description`, `fn`, `parameters_schema`, and `tags`. Can export itself in OpenAI function-calling format via `to_openai_schema()`.

### @tool decorator
Converts a plain Python function into a `Tool` instance. Automatically infers a JSON-Schema from type annotations when no explicit schema is provided.

### SchemaValidator
Performs lightweight JSON-Schema validation (type checking and required-field checking) without external dependencies. Returns a list of human-readable error strings.

### SandboxExecutor
Runs a tool's callable inside a daemon thread with a configurable wall-clock timeout. Returns a `ToolResult` with status `SUCCESS`, `ERROR`, or `TIMEOUT`.

### AuditLogger
Append-only JSONL logger that records every tool invocation — timestamp, tool name, inputs, and the full `ToolResult`. Useful for debugging, compliance, and analytics.

### ToolRegistry
Facade that ties everything together: registration, discovery, input validation, sandboxed execution, and audit logging.

## Data Flow

1. Agent calls `registry.execute(name, inputs)`.
2. Registry looks up the `Tool` by name.
3. `SchemaValidator` checks inputs against the tool's `parameters_schema`.
4. If valid, `SandboxExecutor` runs the tool function with a timeout.
5. `AuditLogger` records the call and result.
6. A `ToolResult` is returned to the caller.

## Configuration

All settings live in `toolsmith.config.Settings` and can be overridden via environment variables (see `.env.example`).
