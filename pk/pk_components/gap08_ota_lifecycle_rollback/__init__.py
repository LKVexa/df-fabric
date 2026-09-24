"""GAP-08 - OTA lifecycle/rollback (master-applied component)."""
from .component import COMPONENT, OtaLifecycleRollbackComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "OtaLifecycleRollbackComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
