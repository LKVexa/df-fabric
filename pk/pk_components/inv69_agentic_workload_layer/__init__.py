"""INV-69 - Agentic workload layer (master-applied component)."""
from .component import COMPONENT, AgenticWorkloadLayerComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "AgenticWorkloadLayerComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
