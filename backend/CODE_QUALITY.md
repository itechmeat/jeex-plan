# Code Quality Guide

## Automatic Checks

To automatically run all code quality checks, use:

```bash
cd backend
bash scripts/lint_format.sh
```

This script will:
1. Format code with `ruff format`
2. Lint and auto-fix with `ruff check --fix`
3. Type check with `mypy`
4. Run tests with `pytest`

## Manual Checks

### 1. Running Ruff formatter (prettier equivalent for Python)
```bash
# Format entire project
ruff format .

# Format specific file
ruff format app/main.py
```

### 2. Running Ruff linter (strict linter)
```bash
# Check all files (without auto-fix)
ruff check .

# Check and auto-fix
ruff check --fix .

# Only for specific directory
ruff check app/

# Check specific rule
ruff check . --select F401  # check for unused imports
```

### 3. Running mypy (type checking)
```bash
# Type check for entire project
mypy app/

# Type check for single file
mypy app/main.py
```

### 4. Running Flake8 (if still needed)
```bash
# Running old linter (now duplicated by ruff)
flake8 app/
```

### 5. Running Black (alternative if used)
```bash
# Format with black
black .
```

### 6. Running isort (import sorting)
```bash
# Ruff now includes isort, but if needed separately:
isort .
```

## Editor Configuration

### VS Code
Add to `.vscode/settings.json`:

```json
{
  "python.formatting.provider": "none",
  "python.linting.enabled": true,
  "ruff.enabled": true,
  "ruff.path": "./.venv/bin/ruff",
  "ruff.args": ["--config", "./backend/pyproject.toml"],
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true,
      "source.fixAll.ruff": true
    },
    "editor.defaultFormatter": "charliermarsh.ruff"
  }
}
```

### Using pre-commit hook (recommended)
Create a `.pre-commit-config.yaml` file in the project root:

```yaml
repos:
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.8.3
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format
```

Then execute:
```bash
pip install pre-commit
pre-commit install
```

## Tool Comparison

| Tool | Purpose | Equivalent |
|------|---------|------------|
| ruff format | Code formatting | Prettier |
| ruff check | Linting | ESLint |
| mypy | Type checking | TypeScript |
| pytest | Testing | Jest |

Ruff is significantly faster than previous tools and provides stricter code checking.