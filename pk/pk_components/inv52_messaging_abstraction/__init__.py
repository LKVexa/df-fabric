"""INV-52 - Messaging abstraction (master-applied component)."""
from .component import COMPONENT, MessagingAbstractionComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "MessagingAbstractionComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
