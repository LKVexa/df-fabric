"""GAP-11 - Accelerator scheduling (master-applied component)."""
from .component import COMPONENT, AcceleratorSchedulingComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "AcceleratorSchedulingComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
