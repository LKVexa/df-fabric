"""INV-56 - Distributed stateful compute (master-applied component)."""
from .component import COMPONENT, DistributedStatefulComputeComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "DistributedStatefulComputeComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
