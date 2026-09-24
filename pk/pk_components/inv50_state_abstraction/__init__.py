"""INV-50 - State abstraction (master-applied component)."""
from .component import COMPONENT, StateAbstractionComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "StateAbstractionComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
