"""INV-51 - Example state stores (master-applied component)."""
from .component import COMPONENT, ExampleStateStoresComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "ExampleStateStoresComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
