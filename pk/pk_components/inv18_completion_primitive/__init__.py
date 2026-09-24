"""INV-18 - Completion primitive (master-applied component)."""
from .component import COMPONENT, CompletionPrimitiveComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "CompletionPrimitiveComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
