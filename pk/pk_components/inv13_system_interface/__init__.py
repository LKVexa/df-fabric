"""INV-13 - System interface (master-applied component)."""
from .component import COMPONENT, SystemInterfaceComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "SystemInterfaceComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
