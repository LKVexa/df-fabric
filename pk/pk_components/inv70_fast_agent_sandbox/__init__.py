"""INV-70 - Fast agent sandbox (master-applied component)."""
from .component import COMPONENT, FastAgentSandboxComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "FastAgentSandboxComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
