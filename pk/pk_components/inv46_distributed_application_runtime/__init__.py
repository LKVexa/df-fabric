"""INV-46 - Distributed application runtime (master-applied component)."""
from .component import COMPONENT, DistributedApplicationRuntimeComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "DistributedApplicationRuntimeComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
