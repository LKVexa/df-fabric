"""INV-15 - New asynchronous ABI (master-applied component)."""
from .component import COMPONENT, NewAsynchronousAbiComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "NewAsynchronousAbiComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
