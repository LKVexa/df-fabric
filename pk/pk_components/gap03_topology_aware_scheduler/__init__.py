"""GAP-03 - Topology-aware scheduler (master-applied component)."""
from .component import COMPONENT, TopologyAwareSchedulerComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "TopologyAwareSchedulerComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
