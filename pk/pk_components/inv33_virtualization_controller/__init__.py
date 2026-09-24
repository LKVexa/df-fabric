"""INV-33 - Virtualization controller (master-applied component)."""
from .component import COMPONENT, VirtualizationControllerComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "VirtualizationControllerComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
