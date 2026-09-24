"""INV-43 - Transient-execution defense (master-applied component)."""
from .component import COMPONENT, TransientExecutionDefenseComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "TransientExecutionDefenseComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
