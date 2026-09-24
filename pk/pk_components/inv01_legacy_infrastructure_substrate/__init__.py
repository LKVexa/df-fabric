"""INV-01 - Legacy infrastructure substrate (master-applied component)."""
from .component import COMPONENT, LegacyInfrastructureSubstrateComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "LegacyInfrastructureSubstrateComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
