"""INV-11 - Interface contract language (master-applied component)."""
from .component import COMPONENT, InterfaceContractLanguageComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "InterfaceContractLanguageComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
