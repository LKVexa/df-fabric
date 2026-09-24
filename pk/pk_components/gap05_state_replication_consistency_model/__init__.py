"""GAP-05 - State replication/consistency model (master-applied component)."""
from .component import COMPONENT, StateReplicationConsistencyModelComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "StateReplicationConsistencyModelComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
