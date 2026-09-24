"""INV-48 - Service communication APIs (master-applied component)."""
from .component import COMPONENT, ServiceCommunicationApisComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "ServiceCommunicationApisComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
