"""INV-10 - Component composition system (master-applied component)."""
from .component import COMPONENT, ComponentCompositionSystemComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "ComponentCompositionSystemComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
