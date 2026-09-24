"""INV-55 - Secrets integration (master-applied component)."""
from .component import COMPONENT, SecretsIntegrationComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "SecretsIntegrationComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
