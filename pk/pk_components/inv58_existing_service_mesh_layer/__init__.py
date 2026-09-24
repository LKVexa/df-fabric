"""INV-58 - Existing service-mesh layer (master-applied component)."""
from .component import COMPONENT, ExistingServiceMeshLayerComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "ExistingServiceMeshLayerComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
