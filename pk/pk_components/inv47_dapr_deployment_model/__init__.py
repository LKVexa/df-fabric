"""INV-47 - Dapr deployment model (master-applied component)."""
from .component import COMPONENT, DaprDeploymentModelComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "DaprDeploymentModelComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
