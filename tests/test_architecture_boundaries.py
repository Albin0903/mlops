"""Architecture boundary tests for API-first core isolation."""

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "app"
DISALLOWED_IMPORT_ROOTS = {"scripts", "tests"}


def _iter_app_python_files() -> list[Path]:
    return sorted(APP_ROOT.rglob("*.py"))


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


def test_app_core_has_no_dependency_on_legacy_or_tests():
    violations: list[str] = []

    for file_path in _iter_app_python_files():
        bad_roots = sorted(_import_roots(file_path) & DISALLOWED_IMPORT_ROOTS)
        if bad_roots:
            rel_path = file_path.relative_to(REPO_ROOT)
            violations.append(f"{rel_path}: {', '.join(bad_roots)}")

    assert not violations, "API core boundary violation(s): app/ must not import legacy modules.\n" + "\n".join(
        violations
    )
