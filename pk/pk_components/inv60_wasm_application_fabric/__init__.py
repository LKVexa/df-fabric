"""INV-60 - Wasm application fabric (master-applied component)."""
from .component import COMPONENT, WasmApplicationFabricComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "WasmApplicationFabricComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
