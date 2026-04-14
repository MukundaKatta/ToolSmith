# ToolSmith — Dynamic Tool Registry. Dynamic tool creation and registry for LLM agents

Dynamic Tool Registry. Dynamic tool creation and registry for LLM agents.

## Why ToolSmith

ToolSmith exists to make this workflow practical. Dynamic tool registry. dynamic tool creation and registry for llm agents. It favours a small, inspectable surface over sprawling configuration.

## Features

- `ToolStatus` — exported from `src/toolsmith/core.py`
- `ToolResult` — exported from `src/toolsmith/core.py`
- `Tool` — exported from `src/toolsmith/core.py`
- Included test suite
- Dedicated documentation folder

## Tech Stack

- **Runtime:** Python

## How It Works

The codebase is organised into `docs/`, `src/`, `tests/`. The primary entry points are `src/toolsmith/core.py`, `src/toolsmith/__init__.py`. `src/toolsmith/core.py` exposes `ToolStatus`, `ToolResult`, `Tool` — the core types that drive the behaviour.

## Getting Started

```bash
pip install -e .
```

## Usage

```python
from toolsmith.core import ToolStatus

instance = ToolStatus()
# See the source for the full API
```

## Project Structure

```
ToolSmith/
├── .env.example
├── CONTRIBUTING.md
├── LICENSE
├── Makefile
├── README.md
├── docs/
├── pyproject.toml
├── src/
├── tests/
```