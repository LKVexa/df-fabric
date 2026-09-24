"""SCH-01 - Workload Classification and Runtime Placement Engine (master-applied component)."""
from .component import COMPONENT, WorkloadClassificationAndRuntimePlacemenComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "WorkloadClassificationAndRuntimePlacemenComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
