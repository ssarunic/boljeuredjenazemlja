"""Coverage gate: every key the server sends is a declared, typed field.

Implements section 10 of specs/api-coverage-specification.md over the redacted
fixtures in ``fixtures/`` (one file per endpoint shape, produced by
``scripts/redact_capture.py``):

1. Every key path observed in a fixture resolves to a declared field of the
   model that receives it (rule R1). Lists are expanded as ``[]``, unions as
   the union of their members.
2. No declared field of any model reachable from the roots is typed ``dict``,
   ``list[dict]`` or ``Any`` (rule R3).
3. Every model reachable from the roots allows extra fields (rule R2).
4. Every fixture validates and no model in the resulting tree has anything in
   ``source_fields``.

Run:
    cd api && pytest src/cadastral_api/tests/test_api_coverage.py
"""

from __future__ import annotations

import json
import types
import typing
from pathlib import Path
from typing import Any

import pytest
from pydantic import AliasChoices, AliasPath, BaseModel

from cadastral_api.models import entities

FIXTURES = Path(__file__).parent / "fixtures"

# Fixture name prefix -> (the server sends a list?, root model).
ROOTS: list[tuple[str, bool, type[BaseModel]]] = [
    ("offices", True, entities.CadastralOffice),
    ("municipalities_", True, entities.MunicipalitySearchResult),
    ("parcel_search_", True, entities.ParcelSearchResult),
    ("possession_sheet_search", True, entities.PossessionSheetSearchResult),
    ("main_books_", True, entities.MainBookSearchResult),
    ("books_of_dc_", True, entities.BookOfDCSearchResult),
    ("parcel_info_", False, entities.ParcelInfo),
    ("lr_unit_", True, entities.LandRegistryUnitDetailed),
    ("file_status_", False, entities.FileStatus),
]


def _root_for(name: str) -> tuple[bool, type[BaseModel]]:
    for prefix, is_list, model in ROOTS:
        if name.startswith(prefix):
            return is_list, model
    raise AssertionError(f"fixture {name} matches no root model; add it to ROOTS")


def _fixtures() -> list[Path]:
    paths = sorted(FIXTURES.glob("*.json"))
    assert paths, f"no fixtures under {FIXTURES}"
    return paths


# ---------------------------------------------------------------------------
# Type introspection
# ---------------------------------------------------------------------------


def _unwrap(annotation: Any) -> list[Any]:
    """The leaf types of an annotation: Optional/Union/Annotated stripped, lists kept."""
    origin = typing.get_origin(annotation)
    if origin is typing.Annotated:
        return _unwrap(typing.get_args(annotation)[0])
    if origin in (typing.Union, types.UnionType):
        leaves: list[Any] = []
        for arg in typing.get_args(annotation):
            leaves.extend(_unwrap(arg))
        return leaves
    return [annotation]


def _is_list(annotation: Any) -> bool:
    return typing.get_origin(annotation) in (list, typing.List)  # noqa: UP006


def _list_item(annotation: Any) -> Any:
    args = typing.get_args(annotation)
    return args[0] if args else Any


def _models_in(annotation: Any) -> list[type[BaseModel]]:
    """Pydantic models an annotation can produce (through Optional/Union/list)."""
    found: list[type[BaseModel]] = []
    for leaf in _unwrap(annotation):
        if _is_list(leaf):
            found.extend(_models_in(_list_item(leaf)))
        elif isinstance(leaf, type) and issubclass(leaf, BaseModel):
            found.append(leaf)
    return found


def _aliases(name: str, field: Any) -> set[str]:
    """Every server key that populates a field (alias, validation aliases, the name)."""
    names = {name}
    if field.alias:
        names.add(field.alias)
    validation_alias = field.validation_alias
    if isinstance(validation_alias, str):
        names.add(validation_alias)
    elif isinstance(validation_alias, AliasChoices):
        for choice in validation_alias.choices:
            if isinstance(choice, str):
                names.add(choice)
            elif isinstance(choice, AliasPath) and choice.path:
                names.add(str(choice.path[0]))
    return names


def _reachable_models(roots: list[type[BaseModel]]) -> list[type[BaseModel]]:
    seen: list[type[BaseModel]] = []
    stack = list(roots)
    while stack:
        model = stack.pop()
        if model in seen:
            continue
        seen.append(model)
        for field in model.model_fields.values():
            stack.extend(_models_in(field.annotation))
    return seen


def _forbidden(annotation: Any) -> bool:
    """True when the annotation admits an untyped mapping or Any (rule R3)."""
    for leaf in _unwrap(annotation):
        if leaf is Any or leaf is dict or typing.get_origin(leaf) is dict:
            return True
        if _is_list(leaf):
            item = _list_item(leaf)
            if item is Any or _forbidden(item):
                return True
    return False


# ---------------------------------------------------------------------------
# Observed key paths
# ---------------------------------------------------------------------------


def _observed_paths(node: Any, prefix: tuple[str, ...] = ()) -> set[tuple[str, ...]]:
    paths: set[tuple[str, ...]] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            path = (*prefix, str(key))
            paths.add(path)
            paths |= _observed_paths(value, path)
    elif isinstance(node, list):
        for item in node:
            paths |= _observed_paths(item, (*prefix, "[]"))
    return paths


def _resolves(path: tuple[str, ...], model: type[BaseModel]) -> bool:
    """Whether ``path`` (server keys and ``[]`` markers) names a declared field."""
    key, rest = path[0], path[1:]
    for name, field in model.model_fields.items():
        if key not in _aliases(name, field):
            continue
        if not rest:
            return True
        annotation = field.annotation
        segments = list(rest)
        leaves = _unwrap(annotation)
        while segments and segments[0] == "[]":
            segments.pop(0)
            items: list[Any] = []
            for leaf in leaves:
                if _is_list(leaf):
                    items.extend(_unwrap(_list_item(leaf)))
            leaves = items
        if not segments:
            return True
        models = [
            leaf for leaf in leaves if isinstance(leaf, type) and issubclass(leaf, BaseModel)
        ]
        return any(_resolves(tuple(segments), sub) for sub in models)
    return False


def _source_fields(node: Any, prefix: str = "") -> list[str]:
    """Paths of every model in a validated tree whose ``source_fields`` is non-empty."""
    found: list[str] = []
    if isinstance(node, BaseModel):
        extra = getattr(node, "source_fields", None)
        if extra is None:
            extra = dict(node.model_extra or {})
        if extra:
            found.append(f"{prefix or type(node).__name__}: {sorted(extra)}")
        for name in type(node).model_fields:
            child_prefix = f"{prefix}.{name}" if prefix else name
            found.extend(_source_fields(getattr(node, name), child_prefix))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            found.extend(_source_fields(item, f"{prefix}[{index}]"))
    return found


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------

ROOT_MODELS = [model for _, _, model in ROOTS]


@pytest.mark.parametrize("path", _fixtures(), ids=lambda p: p.name)
def test_every_observed_key_is_declared(path: Path) -> None:
    """R1: no key in a captured response relies on ``model_extra``."""
    is_list, model = _root_for(path.name)
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data if is_list else [data]
    undeclared: set[str] = set()
    for record in records:
        for key_path in _observed_paths(record):
            if not _resolves(key_path, model):
                undeclared.add(".".join(key_path))
    assert not undeclared, (
        f"{path.name}: keys the {model.__name__} tree does not declare: {sorted(undeclared)}"
    )


def test_no_untyped_fields() -> None:
    """R3: every nested object has a model; no ``dict``, ``list[dict]`` or ``Any`` field."""
    offenders = [
        f"{model.__name__}.{name}: {field.annotation}"
        for model in _reachable_models(ROOT_MODELS)
        for name, field in model.model_fields.items()
        if _forbidden(field.annotation)
    ]
    assert not offenders, "untyped fields: " + ", ".join(offenders)


def test_every_model_allows_extra_fields() -> None:
    """R2: unknown keys are kept (``source_fields``), never dropped."""
    offenders = [
        model.__name__
        for model in _reachable_models(ROOT_MODELS)
        if model.model_config.get("extra") != "allow" or not hasattr(model, "source_fields")
    ]
    assert not offenders, "models without extra='allow' and source_fields: " + ", ".join(offenders)


@pytest.mark.parametrize("path", _fixtures(), ids=lambda p: p.name)
def test_fixture_validates_with_empty_source_fields(path: Path) -> None:
    """Every fixture validates, and nothing lands in ``source_fields`` anywhere in the tree."""
    is_list, model = _root_for(path.name)
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data if is_list else [data]
    leftovers: list[str] = []
    for index, record in enumerate(records):
        instance = model.model_validate(record)
        leftovers.extend(_source_fields(instance, f"[{index}]" if is_list else ""))
    assert not leftovers, f"{path.name}: undeclared server keys: {leftovers}"
