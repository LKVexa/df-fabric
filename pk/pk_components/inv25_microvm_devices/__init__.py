"""INV-25 - MicroVM devices (master-applied component)."""
from .component import COMPONENT, MicrovmDevicesComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "MicrovmDevicesComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
