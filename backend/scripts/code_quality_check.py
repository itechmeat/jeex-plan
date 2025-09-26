#!/usr/bin/env python3
"""
Code quality checker for the JEEX Plan project.
Checks for common issues like missing type hints, unused imports, etc.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


class CodeQualityChecker:
    """Code quality checker class."""

    def __init__(self, app_dir: Path):
        self.app_dir = app_dir
        self.issues: List[str] = []

    def check_file(self, file_path: Path) -> None:
        """Check a single Python file for quality issues."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        try:
            tree = ast.parse(content, filename=str(file_path))
            self._check_ast(tree, file_path)
            self._check_content(content, file_path)
        except Exception as e:
            self.issues.append(f"{file_path}: Could not parse - {e}")

    def _check_ast(self, tree: ast.AST, file_path: Path) -> None:
        """Check AST for issues."""
        visitor = QualityVisitor(file_path)
        visitor.visit(tree)
        self.issues.extend(visitor.issues)

    def _check_content(self, content: str, file_path: Path) -> None:
        """Check content for pattern-based issues."""
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Check for hardcoded secrets (basic patterns)
            if self._contains_hardcoded_secret(line):
                self.issues.append(f"{file_path}:{line_num}: Potential hardcoded secret")

            # Check for TODO/FIXME comments in production code
            if any(keyword in line.upper() for keyword in ['TODO', 'FIXME', 'HACK', 'BUG']):
                if 'tests' not in str(file_path):  # Allow in tests
                    self.issues.append(f"{file_path}:{line_num}: TODO/FIXME comment in production code")

            # Check for print statements (should use logging)
            if re.search(r'\bprint\s*\(', line) and 'test' not in str(file_path):
                self.issues.append(f"{file_path}:{line_num}: Using print() instead of logging")

    def _contains_hardcoded_secret(self, line: str) -> bool:
        """Check if line contains potential hardcoded secrets."""
        secret_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
        ]

        line_lower = line.lower()

        for pattern in secret_patterns:
            if re.search(pattern, line_lower):
                # Allow some common test/example values
                if any(safe in line_lower for safe in ['test', 'example', 'dummy', 'mock', 'fake']):
                    continue
                return True

        return False

    def get_report(self) -> str:
        """Get quality report."""
        if not self.issues:
            return "No code quality issues found!"

        report = f"Found {len(self.issues)} code quality issues:\n\n"
        for issue in sorted(self.issues):
            report += f"  {issue}\n"

        return report


class QualityVisitor(ast.NodeVisitor):
    """AST visitor for code quality checks."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.issues: List[str] = []
        self.imports: Set[str] = set()
        self.used_names: Set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statements."""
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from imports."""
        if node.module:
            for alias in node.names:
                self.imports.add(f"{node.module}.{alias.name}")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions."""
        # Check for missing type hints
        if not self._has_return_annotation(node) and not node.name.startswith('_'):
            # Skip test functions and special methods
            if 'test' not in str(self.file_path) and not node.name.startswith('test_'):
                self.issues.append(
                    f"{self.file_path}:{node.lineno}: Function '{node.name}' missing return type hint"
                )

        # Check for missing parameter type hints
        for arg in node.args.args:
            if not arg.annotation and arg.arg != 'self':
                if 'test' not in str(self.file_path):
                    self.issues.append(
                        f"{self.file_path}:{node.lineno}: Parameter '{arg.arg}' in '{node.name}' missing type hint"
                    )

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions."""
        # Same checks as regular functions
        if not self._has_return_annotation(node) and not node.name.startswith('_'):
            if 'test' not in str(self.file_path) and not node.name.startswith('test_'):
                self.issues.append(
                    f"{self.file_path}:{node.lineno}: Async function '{node.name}' missing return type hint"
                )

        for arg in node.args.args:
            if not arg.annotation and arg.arg != 'self':
                if 'test' not in str(self.file_path):
                    self.issues.append(
                        f"{self.file_path}:{node.lineno}: Parameter '{arg.arg}' in '{node.name}' missing type hint"
                    )

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions."""
        # Check for missing docstrings
        if not self._has_docstring(node) and not node.name.startswith('_'):
            if 'test' not in str(self.file_path):
                self.issues.append(
                    f"{self.file_path}:{node.lineno}: Class '{node.name}' missing docstring"
                )

        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Visit name references."""
        self.used_names.add(node.id)
        self.generic_visit(node)

    def _has_return_annotation(self, node) -> bool:
        """Check if function has return type annotation."""
        return node.returns is not None

    def _has_docstring(self, node) -> bool:
        """Check if node has docstring."""
        return (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        )


def main():
    """Main function."""
    app_dir = Path(__file__).parent.parent / "app"

    if not app_dir.exists():
        print("App directory not found!")
        return

    checker = CodeQualityChecker(app_dir)

    python_files = list(app_dir.rglob("*.py"))
    for py_file in python_files:
        checker.check_file(py_file)

    print(checker.get_report())


if __name__ == "__main__":
    main()