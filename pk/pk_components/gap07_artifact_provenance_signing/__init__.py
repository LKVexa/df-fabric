"""GAP-07 - Artifact provenance/signing (master-applied component)."""
from .component import COMPONENT, ArtifactProvenanceSigningComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "ArtifactProvenanceSigningComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
