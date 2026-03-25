# 🔥 ToolSmith

> Dynamic tool creation and registry for LLM agents

[![CI](https://github.com/MukundaKatta/ToolSmith/actions/workflows/ci.yml/badge.svg)](https://github.com/MukundaKatta/ToolSmith/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)]()

## What is ToolSmith?
ToolSmith is a tool registry and execution framework for LLM agents. Define tools with JSON schemas, register them at runtime, validate inputs, and execute them safely — all with built-in sandboxing and audit logging.

## ✨ Features
- ✅ JSON Schema-based tool definitions
- ✅ Runtime tool registration and discovery
- ✅ Input validation against schemas
- ✅ Execution sandboxing with timeouts
- ✅ Audit logging of all tool calls
- 🔜 Tool composition (chain tools together)
- 🔜 Natural language tool creation

## 🚀 Quick Start
```bash
pip install toolsmith-ai
```
```python
from toolsmith import ToolRegistry, tool

registry = ToolRegistry()

@tool(name="calculator", description="Perform math operations")
def calculator(expression: str) -> float:
    return eval(expression)  # sandboxed in production

registry.register(calculator)
result = registry.execute("calculator", {"expression": "2 + 2"})
```

## 🏗️ Architecture
```mermaid
graph TD
    A[Tool Definition] --> B[Schema Validator]
    B --> C[Tool Registry]
    C --> D{Execute}
    D --> E[Sandbox]
    E --> F[Result]
    D --> G[Audit Log]
```

## 📖 Inspired By
Inspired by OpenAI's function calling and Anthropic's tool use patterns, but built as a standalone framework for any agent system.

---
**Built by [Officethree Technologies](https://github.com/MukundaKatta)** | Made with ❤️ and AI
