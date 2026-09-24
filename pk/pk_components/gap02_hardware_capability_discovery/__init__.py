"""GAP-02 - Hardware capability discovery (master-applied component)."""
from .component import COMPONENT, HardwareCapabilityDiscoveryComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "HardwareCapabilityDiscoveryComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
