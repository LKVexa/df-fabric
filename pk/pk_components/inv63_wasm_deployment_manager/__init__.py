"""INV-63 - Wasm deployment manager (master-applied component)."""
from .component import COMPONENT, WasmDeploymentManagerComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "WasmDeploymentManagerComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
