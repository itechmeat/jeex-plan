#!/bin/bash
# Script for automatic code quality checks and formatting
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$SCRIPT_DIR/.."

echo "Running Ruff formatter..."
ruff format .

echo "Running Ruff linter with auto-fix where possible..."
ruff check --fix .

echo "Running mypy for type checking..."
mypy app/

echo "Running tests to ensure changes didn't break anything..."
pytest

echo "All code quality checks passed!"
