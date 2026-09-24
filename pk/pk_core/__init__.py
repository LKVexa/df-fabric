"""pk_core - Post-Kubernetes master-applied component runtime.

Shared substrate for components generated from the Post-Kubernetes Master
Prompt & Workflow Series v4.0.0.  Every architectural element becomes a
:class:`~pk_core.component.Component` that carries a binding contract, answers
all 100 checklist requirements of its element across the ten checklist
dimensions, and emits a hash-chained W0-W9 evidence record.
"""
__version__ = "4.0.0"

from pk_core.identity import DIMENSIONS, STAGES, Dimension, ElementId, Stage
from pk_core.contract import Contract
from pk_core.checklist import Checklist, ChecklistItem, Finding, Status
from pk_core.component import Component
from pk_core.evidence import EvidenceLedger, EvidenceRecord
from pk_core.workflow import WorkflowEngine, WorkflowResult
from pk_core.registry import Registry
from pk_core.gate import ConformanceGate, GateResult
from pk_core.integration import installed, resolve

__all__ = [
    "DIMENSIONS", "STAGES", "Dimension", "ElementId", "Stage",
    "Contract", "Checklist", "ChecklistItem", "Finding", "Status",
    "Component", "EvidenceLedger", "EvidenceRecord",
    "WorkflowEngine", "WorkflowResult", "Registry",
    "ConformanceGate", "GateResult", "resolve", "installed", "__version__",
]
