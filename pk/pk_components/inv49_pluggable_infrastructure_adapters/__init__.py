"""INV-49 - Pluggable infrastructure adapters (master-applied component)."""
from .component import COMPONENT, PluggableInfrastructureAdaptersComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "PluggableInfrastructureAdaptersComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
