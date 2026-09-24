"""INV-65 - Capability providers (master-applied component)."""
from .component import COMPONENT, CapabilityProvidersComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "CapabilityProvidersComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
