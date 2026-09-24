"""INV-72 - Accelerated workload requirement (master-applied component)."""
from .component import COMPONENT, AcceleratedWorkloadRequirementComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "AcceleratedWorkloadRequirementComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
