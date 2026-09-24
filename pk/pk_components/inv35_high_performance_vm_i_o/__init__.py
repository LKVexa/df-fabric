"""INV-35 - High-performance VM I/O (master-applied component)."""
from .component import COMPONENT, HighPerformanceVmIOComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "HighPerformanceVmIOComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
