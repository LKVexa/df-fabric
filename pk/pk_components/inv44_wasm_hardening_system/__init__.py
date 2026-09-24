"""INV-44 - Wasm hardening system (master-applied component)."""
from .component import COMPONENT, WasmHardeningSystemComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "WasmHardeningSystemComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
