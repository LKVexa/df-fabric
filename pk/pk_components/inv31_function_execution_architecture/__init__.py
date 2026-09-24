"""INV-31 - Function execution architecture (master-applied component)."""
from .component import COMPONENT, FunctionExecutionArchitectureComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "FunctionExecutionArchitectureComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
