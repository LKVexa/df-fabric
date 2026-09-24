"""GAP-04 - Disconnected-operation controller (master-applied component)."""
from .component import COMPONENT, DisconnectedOperationControllerComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "DisconnectedOperationControllerComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
