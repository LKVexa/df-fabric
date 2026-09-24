"""INV-07 - GitOps transition layer (master-applied component)."""
from .component import COMPONENT, GitopsTransitionLayerComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "GitopsTransitionLayerComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
