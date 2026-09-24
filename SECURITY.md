# Security boundaries

This is a local reference implementation. Treat PA-LCTL inputs and manifest
evidence as untrusted. Integrity verification rejects traversal, duplicate
entries, malformed digests and filesystem links/reparse points. Run verification
on a tree not concurrently writable by an adversary; filesystem races are not
eliminated by these checks.

The Photon UI is loopback-only. Do not expose it through a public proxy. Its
launch token is a local session secret. Do not commit generated runtime state,
browser profiles, execution receipts or credentials. Photon host execution stays
blocked in the shipped VENDORED_UNBOUND profile. Synthetic test receipts do not
constitute host attestation.

Checksums stored with the code detect changes but cannot establish independent
publisher identity. Native VM behavior, hardware isolation, cross-host transport
and deployment operations need separate environment-specific validation.

Report reproducible issues to the repository owner through GitHub. Do not post
credentials or private runtime data in public issues.
