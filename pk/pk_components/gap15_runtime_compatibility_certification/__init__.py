"""GAP-15 - Runtime compatibility certification (master-applied component)."""
from .component import COMPONENT, RuntimeCompatibilityCertificationComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "RuntimeCompatibilityCertificationComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
