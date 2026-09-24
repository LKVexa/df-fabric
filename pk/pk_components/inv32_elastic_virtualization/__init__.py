"""INV-32 - Elastic virtualization (master-applied component)."""
from .component import COMPONENT, ElasticVirtualizationComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "ElasticVirtualizationComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
