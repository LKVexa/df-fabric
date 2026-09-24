# Open conditions -- DF_Fabric

Gate verdict: **CONDITIONAL_GO** across 95 element(s).

Every line below is a requirement recorded `partial` rather than claimed as
satisfied. Each names what is missing and what it waits on. Conditions on elements
this project does not own are listed for visibility and are cleared by their owner.

## GAP-07 -- Artifact provenance/signing  *(owned elsewhere)*

- **GAP-07-C049** (W5) -- Signatures are HMAC-based for a self-contained reference build; asymmetric keys with external custody and a transparency log are specified and belong with the estate's real KMS.
  - *waiting on:* requires key custody outside this element's scope

## Cleared so far

Twenty-two requirements that earlier batches recorded as `partial` are now satisfied by
a real call into a sibling element rather than a promise.

Batch 2 cleared twelve: PLN-02-C053, PLN-03-C043, PLN-03-C056, PLN-04-C044,
PLN-04-C052, PLN-05-C041, PLN-06-C041, PLN-07-C049, PLN-07-C054, SCH-01-C058,
GAP-02-C045 and GAP-10-C041.

Batch 3 cleared five more: PLN-05-C065 (cold-start budget, by INV-26 restore),
SCH-01-C055 (lease reclamation, by INV-33), INV-24-C061 (throughput, by INV-35),
INV-26-C045 (snapshot signing, by GAP-07) and INV-30-C051 (hardware presence, by GAP-02).

Batch 4 cleared two: INV-29's hybrid composition now links the Wasm and unikernel
layers on INV-11's typed interfaces instead of bare import names, so a drifted
signature is refused rather than name-matched; and INV-16's cancellation is now
demonstrated end to end over INV-15's real asynchronous ABI, so a caller that
disappears is shown to take its subtasks with it.

Batch 5 cleared the two that waited on the transports: GAP-12-C050 (relayed traffic is now
sealed end to end by INV-36, so a relay forwards ciphertext it cannot read or alter undetected)
and PLN-06-C054 (integrity is verified end to end by the receiver through INV-37 rather than
taken from the transport).

Batch 6 cleared GAP-05-C053: the conflict set is now bounded, with a documented
shedding policy -- writes past the bound are quarantined with their reason, never
dropped and never allowed to evict an existing sibling.

One condition remains, and it is genuinely outside this payload: GAP-07-C049.
Signatures are HMAC-based so the reference build is self-contained; asymmetric keys
with external custody and a transparency log need the estate's real KMS, and no
code in this payload can honestly stand in for that.

## Clearing a condition

Replace the `partial` finding in the element's `component.py` with a `satisfied`
finding citing the artifact that proves it, then re-run:

```
python SELFTEST.py
python -m pk_core gate --out conformance/PK_GATE_RESULTS.json
```

The gate returns `GO` once no element reports a partial requirement.
