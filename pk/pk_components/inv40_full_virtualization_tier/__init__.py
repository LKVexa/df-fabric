"""INV-40 - Full virtualization tier (master-applied component)."""
from .component import COMPONENT, FullVirtualizationTierComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "FullVirtualizationTierComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
