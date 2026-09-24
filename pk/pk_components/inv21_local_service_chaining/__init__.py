"""INV-21 - Local service chaining (master-applied component)."""
from .component import COMPONENT, LocalServiceChainingComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "LocalServiceChainingComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
