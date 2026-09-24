"""INV-08 - Dynamic infrastructure model (master-applied component)."""
from .component import COMPONENT, DynamicInfrastructureModelComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "DynamicInfrastructureModelComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
