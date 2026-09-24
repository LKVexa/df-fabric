"""INV-71 - Heavy agent sandbox (master-applied component)."""
from .component import COMPONENT, HeavyAgentSandboxComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "HeavyAgentSandboxComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
