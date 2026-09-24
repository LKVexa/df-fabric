"""INV-62 - Edge topology (master-applied component)."""
from .component import COMPONENT, EdgeTopologyComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "EdgeTopologyComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
