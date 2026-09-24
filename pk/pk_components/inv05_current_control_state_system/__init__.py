"""INV-05 - Current control-state system (master-applied component)."""
from .component import COMPONENT, CurrentControlStateSystemComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "CurrentControlStateSystemComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
