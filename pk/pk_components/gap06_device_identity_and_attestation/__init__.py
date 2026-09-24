"""GAP-06 - Device identity and attestation (master-applied component)."""
from .component import COMPONENT, DeviceIdentityAndAttestationComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "DeviceIdentityAndAttestationComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
