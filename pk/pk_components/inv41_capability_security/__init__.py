"""INV-41 - Capability security (master-applied component)."""
from .component import COMPONENT, CapabilitySecurityComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "CapabilitySecurityComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
