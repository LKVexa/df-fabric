"""INV-59 - Application authorization (master-applied component)."""
from .component import COMPONENT, ApplicationAuthorizationComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "ApplicationAuthorizationComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
