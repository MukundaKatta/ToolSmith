# Contributing to ToolSmith

Thank you for your interest in contributing! Here's how to get started.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/MukundaKatta/ToolSmith.git
cd ToolSmith

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
make install
```

## Running Tests

```bash
make test
```

## Code Quality

```bash
make lint        # ruff linter
make typecheck   # mypy strict mode
make fmt         # auto-format with ruff
```

## Pull Request Process

1. Fork the repository and create a feature branch from `main`.
2. Write tests for any new functionality.
3. Ensure all checks pass: `make all`.
4. Open a pull request with a clear description of the change.

## Code Style

- Python 3.11+ features are welcome (type unions with `|`, etc.).
- Keep functions short and well-documented.
- Follow existing patterns in `src/toolsmith/core.py`.

## Reporting Issues

Open a GitHub issue with steps to reproduce, expected behaviour, and actual behaviour.
