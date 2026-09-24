"""INV-34 - Legacy CPU expansion path (master-applied component)."""
from .component import COMPONENT, LegacyCpuExpansionPathComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "LegacyCpuExpansionPathComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
