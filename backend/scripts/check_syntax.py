#!/usr/bin/env python3
"""
Syntax checker for Python files in the project.
"""

import ast
import sys
from pathlib import Path


def check_syntax(file_path: Path) -> tuple[bool, str]:
    """Check syntax of a Python file."""
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        # Try to parse the file
        ast.parse(content, filename=str(file_path))
        return True, ""
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def main():
    """Main function to check all Python files."""
    app_dir = Path(__file__).parent.parent / "app"

    if not app_dir.exists():
        print("App directory not found!")
        sys.exit(1)

    python_files = list(app_dir.rglob("*.py"))
    errors = []

    for py_file in python_files:
        success, error = check_syntax(py_file)
        if not success:
            errors.append(f"{py_file}: {error}")

    if errors:
        print(f"Found {len(errors)} syntax errors:")
        for error in errors:
            print(f"  {error}")
        sys.exit(1)
    else:
        print(f"All {len(python_files)} Python files are syntactically correct!")


if __name__ == "__main__":
    main()
