"""Resolving one element's dependency on another at run time.

Elements are routed to the project that owns them, but an element may still
need a sibling to discharge a requirement -- PLN-07 cannot bind a grant to a
signature without GAP-07, and PLN-04 cannot root attestation without GAP-06.

``resolve`` looks the sibling up in the installed component package and returns
``None`` when it is not installed.  A component that cannot resolve a sibling
records the affected requirement as ``partial`` naming the missing element,
rather than claiming an integration that is not there.  The same component
therefore reports honestly in a full estate install and in a partial one.
"""
from __future__ import annotations

import importlib
import json
from functools import lru_cache
from pathlib import Path

DEFAULT_PACKAGE = "pk_components"


@lru_cache(maxsize=None)
def _index(package: str = DEFAULT_PACKAGE) -> dict[str, str]:
    """Map element id -> module name for every installed component package."""
    try:
        root = importlib.import_module(package)
    except ModuleNotFoundError:
        return {}
    import pkgutil

    found: dict[str, str] = {}
    for info in pkgutil.iter_modules(root.__path__):
        if not info.ispkg:
            continue
        checklist = Path(root.__path__[0]) / info.name / "CHECKLIST.json"
        if not checklist.exists():
            continue
        try:
            element = json.loads(checklist.read_text(encoding="utf-8"))["element"]
        except (ValueError, KeyError):
            continue
        found[element] = f"{package}.{info.name}"
    return found


def resolve(element_id: str, package: str = DEFAULT_PACKAGE):
    """Return the installed component module for ``element_id``, or None."""
    module = _index(package).get(element_id)
    if module is None:
        return None
    try:
        return importlib.import_module(f"{module}.component")
    except ModuleNotFoundError:
        return None


def installed(package: str = DEFAULT_PACKAGE) -> list[str]:
    return sorted(_index(package))


def ownership(root: str | Path) -> set[str]:
    """Elements this installation owns, from PK_OWNERSHIP.json; all of them if absent."""
    path = Path(root) / "PK_OWNERSHIP.json"
    if not path.exists():
        return set(installed())
    return set(json.loads(path.read_text(encoding="utf-8"))["owns"])
