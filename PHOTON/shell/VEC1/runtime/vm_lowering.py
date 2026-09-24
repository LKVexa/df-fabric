from __future__ import annotations
from .canonical import sha256_json

def witness_for(payload) -> int:
    """Project the canonical payload SHA-256 into an actual unsigned low-64 witness.

    v0.3.0 used the first eight hex digits (32 bits) while labeling the value
    `witness_low64`.  Using the digest's final sixteen hex digits both matches
    the field name and exercises the adapters' full 64-bit result lane.
    """
    return int(sha256_json(payload)[-16:], 16)

def lower_small(w: int) -> str:
    return f""".profile SIM_CORE
.image_version 3
.request_caps CONTROL|ARITH
MOVI.WRAP R0, {w}, C0
MOVI.WRAP R1, 0, C0
ADD.CHECKED R2, R0, R1, C0
HALT.WRAP C0
"""

def lower_medium(w: int) -> str:
    return f"""LCTLC/1.1
@unit id=vec1.witness version=4.7.0 profile=brvm-native entry=W00001 target=local-reference backend=brir network=deny replay=deterministic image_version=9 requested_caps=CONTROL|ARITH max_steps=8 termination=bounded
@defaults mode=WRAP width=WIDE
@frame id=F0000 parent=ROOT module=vec1.witness
ID│LANE│OP│OUT│CTRL│IN│ARG│META
W00001│w│MOVI│R0│C0│_│u64:{w}│width=WIDE
W00002│w│MOVI│R1│C0│_│u64:0│width=WIDE
W00003│w│ADD│R3│C0│R0›R1│_│mode=WRAP;width=WIDE
W00004│w│MOV│R2│C0│R3│_│width=WIDE
W00005│w│HALT│_│C0│_│_│_
@end
"""

def lower_large(w: int) -> str:
    return f"""LCTLC/1.2
@unit id=vec1.witness version=4.3.0 language=columned-lctl/4.3 isa=BR/1.1 br_image_version=10 br_request_caps=CONTROL|ARITH
@defaults mode=WRAP width=WIDE
ID│LANE│OP│OUT│CTRL│IN│ARG│META
W00001│exec│MOVI│R0│C0:CONTROL│_│imm={w}│_
W00002│exec│MOVI│R1│C0:CONTROL│_│imm=0│_
W00003│exec│ADD│R2│C0:ARITH│R0›R1│_│_
W00004│exec│HALT│_│C0:CONTROL│_│_│_
@end
"""

def lower_xlarge(w: int) -> str:
    return f"""LCTLC/1.0
@unit id=vec1.witness version=1.0.0 profile=native program_version=1
@defaults qspace=H basis=computational regime=exact assume=finite_dimension error=exact conf=1.0
@frame id=F0000 parent=ROOT module=vec1.witness
ID│LANE│OP│OUT│CTRL│IN│ARG│META
D0001│alloc│Q│q│_│_│1│res="logical_qubits=1";p=lctl:1.2
D0002│alloc│C│c│_│_│1│res="classical_bits=1";p=lctl:1.2
V0001│vm│REG│_│_│_│vm.op=MOVI;dst=R0;imm={w}│p=quorum:vm5
V0002│vm│REG│_│_│_│vm.op=HALT│p=quorum:vm5
C9999│terminal│.│_│_│_│terminal=sealed_graph_end;justification=canonical_entry_sentinel│p=lctl:nop
@end
"""

LOWERERS={
    "N_SMALL":("mssl",lower_small),
    "N_MEDIUM":("lctlc",lower_medium),
    "N_LARGE":("lctlc",lower_large),
    "N_XLARGE":("lctlc",lower_xlarge),
}
