"""INV-24 - MicroVM runtime (master-applied component)."""
from .component import COMPONENT, MicrovmRuntimeComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "MicrovmRuntimeComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
