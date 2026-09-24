"""INV-02 - Container substrate (master-applied component)."""
from .component import COMPONENT, ContainerSubstrateComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "ContainerSubstrateComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
