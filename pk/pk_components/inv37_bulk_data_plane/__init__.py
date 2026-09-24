"""INV-37 - Bulk data plane (master-applied component)."""
from .component import COMPONENT, BulkDataPlaneComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "BulkDataPlaneComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
