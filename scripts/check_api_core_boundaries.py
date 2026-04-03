#!/usr/bin/env python3
"""Fail if app/ imports legacy or test modules."""

import ast
from pathlib import Path


DISALLOWED_IMPORT_ROOTS = {"scripts", "tests"}


def _iter_app_python_files(app_root: Path) -> list[Path]:
    return sorted(app_root.rglob("*.py"))


def _import_roots(file_path: Path) -> set[str]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    roots: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])

    return roots


def _collect_violations(repo_root: Path) -> list[str]:
    app_root = repo_root / "app"
    violations: list[str] = []

    for file_path in _iter_app_python_files(app_root):
        bad_roots = sorted(_import_roots(file_path) & DISALLOWED_IMPORT_ROOTS)
        if bad_roots:
            rel_path = file_path.relative_to(repo_root)
            violations.append(f"{rel_path}: {', '.join(bad_roots)}")

    return violations


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    violations = _collect_violations(repo_root)
    if not violations:
        print("info: API core boundaries OK")
        return 0

    print("error: API core boundary violation(s) detected:")
    for violation in violations:
        print(f"  - {violation}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
