"""INV-64 - Application model (master-applied component)."""
from .component import COMPONENT, ApplicationModelComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "ApplicationModelComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
