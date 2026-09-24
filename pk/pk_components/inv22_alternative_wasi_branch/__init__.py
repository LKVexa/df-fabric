"""INV-22 - Alternative WASI branch (master-applied component)."""
from .component import COMPONENT, AlternativeWasiBranchComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "AlternativeWasiBranchComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
