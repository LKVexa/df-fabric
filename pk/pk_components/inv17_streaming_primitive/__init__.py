"""INV-17 - Streaming primitive (master-applied component)."""
from .component import COMPONENT, StreamingPrimitiveComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "StreamingPrimitiveComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
