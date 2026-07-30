from __future__ import annotations

import ast
import importlib
from pathlib import Path
from types import ModuleType

import pytest


SOURCE_ROOT = Path(__file__).parents[1] / "src/twinforge"
NEUTRAL_FORBIDDEN_PREFIXES = (
    "twinforge.converters",
    "twinforge.exporters",
    "twinforge.parsers",
    "twinforge.targets",
)
EXPORTER_TARGET_COMPATIBILITY_FILES = {
    Path("__init__.py"),
    Path("powerflex525_iec.py"),
}


def _module_package(path: Path) -> tuple[str, ...]:
    relative = path.relative_to(SOURCE_ROOT)
    return ("twinforge", *relative.parent.parts)


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    package = _module_package(path)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                retained = package[: len(package) - (node.level - 1)]
                parts = (*retained, *((node.module or "").split(".")))
                imported.add(".".join(part for part in parts if part))
            elif node.module:
                imported.add(node.module)
    return imported


@pytest.mark.parametrize("area", ["model", "ir"])
def test_neutral_layers_do_not_depend_on_conversion_or_targets(
    area: str,
) -> None:
    violations: list[str] = []
    for path in sorted((SOURCE_ROOT / area).rglob("*.py")):
        for dependency in sorted(_imported_modules(path)):
            if dependency.startswith(NEUTRAL_FORBIDDEN_PREFIXES):
                violations.append(
                    f"{path.relative_to(SOURCE_ROOT)} -> {dependency}"
                )

    assert violations == []


def test_exporter_to_target_imports_are_compatibility_only() -> None:
    violations: list[str] = []
    exporters = SOURCE_ROOT / "exporters"
    for path in sorted(exporters.rglob("*.py")):
        relative = path.relative_to(exporters)
        target_dependencies = sorted(
            dependency
            for dependency in _imported_modules(path)
            if dependency.startswith("twinforge.targets")
        )
        if (
            target_dependencies
            and relative not in EXPORTER_TARGET_COMPATIBILITY_FILES
        ):
            violations.extend(
                f"{relative} -> {dependency}"
                for dependency in target_dependencies
            )

    assert violations == []


@pytest.mark.parametrize(
    "module_name",
    [
        "twinforge.exporters",
        "twinforge.targets.codesys",
        "twinforge.targets.openplc",
    ],
)
def test_public_exports_are_unique_and_resolvable(module_name: str) -> None:
    module: ModuleType = importlib.import_module(module_name)
    exported = module.__all__

    assert len(exported) == len(set(exported))
    assert [
        name for name in exported if not hasattr(module, name)
    ] == []
