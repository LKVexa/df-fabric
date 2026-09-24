"""INV-67 - Kubernetes integration mechanism (master-applied component)."""
from .component import COMPONENT, KubernetesIntegrationMechanismComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "KubernetesIntegrationMechanismComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
