"""GAP-10 - Power/thermal-aware scheduling (master-applied component)."""
from .component import COMPONENT, PowerThermalAwareSchedulingComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["COMPONENT", "PowerThermalAwareSchedulingComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
