from __future__ import annotations

WORKLOAD_TIER = {
    "interactive_state":"N_SMALL",
    "object_edit":"N_SMALL",
    "animation_tick":"N_SMALL",
    "semantic_validation":"N_MEDIUM",
    "ocr_bridge":"N_MEDIUM",
    "checkpoint":"N_MEDIUM",
    "device_io":"N_LARGE",
    "file_import_export":"N_LARGE",
    "host_service":"N_LARGE",
    "heavy_compute":"N_XLARGE",
    "long_running":"N_XLARGE",
    "quorum":"N_XLARGE",
}

FALLBACK_ORDER = {
    "N_SMALL":["N_SMALL","N_MEDIUM","N_LARGE","N_XLARGE"],
    "N_MEDIUM":["N_MEDIUM","N_LARGE","N_XLARGE","N_SMALL"],
    "N_LARGE":["N_LARGE","N_XLARGE","N_MEDIUM","N_SMALL"],
    "N_XLARGE":["N_XLARGE","N_LARGE","N_MEDIUM","N_SMALL"],
}

def place(workload: str, bound_nodes):
    preferred=WORKLOAD_TIER.get(workload,"N_MEDIUM")
    bound=set(bound_nodes)
    for node in FALLBACK_ORDER[preferred]:
        if node in bound:
            return {
                "workload":workload,
                "preferred":preferred,
                "selected":node,
                "degraded":node!=preferred,
                "reason":"preferred tier available" if node==preferred else f"preferred tier unavailable; deterministic fallback selected {node}"
            }
    return {"workload":workload,"preferred":preferred,"selected":None,"degraded":True,"reason":"no bound VM nodes"}
