"""GAP-12 - WAN resilience and NAT traversal (master-applied component)."""
from .component import COMPONENT, WanResilienceAndNatTraversalComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "WanResilienceAndNatTraversalComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
