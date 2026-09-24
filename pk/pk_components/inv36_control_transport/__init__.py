"""INV-36 - Control transport (master-applied component)."""
from .component import COMPONENT, ControlTransportComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "ControlTransportComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
