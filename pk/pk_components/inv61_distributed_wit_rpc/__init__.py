"""INV-61 - Distributed WIT RPC (master-applied component)."""
from .component import COMPONENT, DistributedWitRpcComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "DistributedWitRpcComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
