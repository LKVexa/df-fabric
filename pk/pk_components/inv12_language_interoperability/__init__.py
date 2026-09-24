"""INV-12 - Language interoperability (master-applied component)."""
from .component import COMPONENT, LanguageInteroperabilityComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "LanguageInteroperabilityComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
