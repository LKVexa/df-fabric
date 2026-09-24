"""INV-06 - Traditional IaC (master-applied component)."""
from .component import COMPONENT, TraditionalIacComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "TraditionalIacComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
