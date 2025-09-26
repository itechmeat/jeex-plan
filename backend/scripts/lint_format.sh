#!/bin/bash
# Script for automatic code quality checks and formatting

set -e  # Exit immediately if a command exits with a non-zero status

echo "Running Ruff formatter..."
ruff format .

echo "Running Ruff linter with auto-fix where possible..."
ruff check --fix .

echo "Running mypy for type checking..."
mypy app/

echo "Running tests to ensure changes didn't break anything..."
pytest

echo "All code quality checks passed!"