"""INV-23 - Hardware virtualization primitive (master-applied component)."""
from .component import COMPONENT, HardwareVirtualizationPrimitiveComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "HardwareVirtualizationPrimitiveComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
