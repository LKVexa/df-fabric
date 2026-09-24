"""INV-26 - MicroVM snapshotting (master-applied component)."""
from .component import COMPONENT, MicrovmSnapshottingComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "MicrovmSnapshottingComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
