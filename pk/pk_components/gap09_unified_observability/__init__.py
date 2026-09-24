"""GAP-09 - Unified observability (master-applied component)."""
from .component import COMPONENT, UnifiedObservabilityComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "UnifiedObservabilityComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
