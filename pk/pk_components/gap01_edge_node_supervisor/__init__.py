"""GAP-01 - Edge Node Supervisor (master-applied component)."""
from .component import COMPONENT, EdgeNodeSupervisorComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "EdgeNodeSupervisorComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
