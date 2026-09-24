"""GAP-14 - Data-gravity manager (master-applied component)."""
from .component import COMPONENT, DataGravityManagerComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "DataGravityManagerComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
