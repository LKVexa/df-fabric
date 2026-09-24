"""INV-66 - Enterprise Wasm control plane (master-applied component)."""
from .component import COMPONENT, EnterpriseWasmControlPlaneComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "EnterpriseWasmControlPlaneComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
