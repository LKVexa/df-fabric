"""INV-68 - Resource packing (master-applied component)."""
from .component import COMPONENT, ResourcePackingComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "ResourcePackingComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
