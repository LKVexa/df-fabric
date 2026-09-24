"""INV-19 - OS asynchronous analogues (master-applied component)."""
from .component import COMPONENT, OsAsynchronousAnaloguesComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "OsAsynchronousAnaloguesComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
