"""Discovery of installed components."""
from __future__ import annotations

import importlib
import inspect
import pkgutil

from pk_core.component import Component


class Registry:
    """Discovers and holds the component classes installed under a package."""

    def __init__(self, package: str = "pk_components") -> None:
        self.package = package
        self._classes: dict[str, type[Component]] = {}

    def discover(self) -> "Registry":
        try:
            root = importlib.import_module(self.package)
        except ModuleNotFoundError:
            return self
        for info in pkgutil.iter_modules(root.__path__):
            if not info.ispkg:
                continue
            module = importlib.import_module(f"{self.package}.{info.name}")
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Component) and obj is not Component and obj.element_id:
                    self._classes[obj.element_id] = obj
        return self

    def register(self, cls: type[Component]) -> None:
        self._classes[cls.element_id] = cls

    def __len__(self) -> int:
        return len(self._classes)

    def __contains__(self, element_id: str) -> bool:
        return element_id in self._classes

    def ids(self) -> list[str]:
        return sorted(self._classes)

    def get(self, element_id: str) -> Component:
        return self._classes[element_id]()

    def instantiate(self) -> list[Component]:
        return [self._classes[e]() for e in self.ids()]
