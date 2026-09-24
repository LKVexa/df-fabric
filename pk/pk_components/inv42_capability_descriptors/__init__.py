"""INV-42 - Capability descriptors (master-applied component)."""
from .component import COMPONENT, CapabilityDescriptorsComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "CapabilityDescriptorsComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
