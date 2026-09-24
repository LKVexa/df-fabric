from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from .canonical import canonical_json, sha256_text, strict_json_loads

GENESIS = "0" * 64


class LedgerIntegrityError(RuntimeError):
    pass


class AppendOnlyLedger:
    """Hash-chained, append-only JSONL event ledger.

    The verified head is cached as (seq, hash, byte size, mtime_ns). Appends and
    dashboard health checks are O(1) while the on-disk fingerprint is unchanged.
    Any size/mtime change forces a streaming full-chain verification before the
    next append/health result. Full verification uses O(1) event memory.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._head = None  # (seq, hash, size, mtime_ns)

    def _fingerprint(self):
        try:
            st = self.path.stat()
            return st.st_size, st.st_mtime_ns
        except FileNotFoundError:
            return 0, 0

    def verify(self):
        """Stream-verify the complete ledger without retaining all events."""
        with self._lock:
            size, mtime = self._fingerprint()
            prev = GENESIS
            count = 0
            if self.path.exists():
                with self.path.open("r", encoding="utf-8") as f:
                    for line_no, line in enumerate(f, 1):
                        if not line.strip():
                            continue
                        try:
                            event = strict_json_loads(line)
                        except Exception as e:
                            raise LedgerIntegrityError(f"invalid ledger JSON at line {line_no}: {e}") from e
                        if not isinstance(event, dict):
                            raise LedgerIntegrityError(f"ledger entry at line {line_no} is not an object")
                        count += 1
                        body = {k: v for k, v in event.items() if k != "event_hash"}
                        if event.get("seq") != count:
                            raise LedgerIntegrityError(f"sequence mismatch at event {count}")
                        if event.get("prev_hash") != prev:
                            raise LedgerIntegrityError(f"previous hash mismatch at event {count}")
                        expected = sha256_text(canonical_json(body))
                        if event.get("event_hash") != expected:
                            raise LedgerIntegrityError(f"event hash mismatch at event {count}")
                        prev = expected
            self._head = (count, prev, size, mtime)
            return {"ok": True, "events": count, "head": prev}

    def _current_head(self):
        if self._head is None or (self._head[2], self._head[3]) != self._fingerprint():
            self.verify()
        return self._head

    def health(self):
        """Return the verified cached head, re-verifying only after file change."""
        with self._lock:
            seq, head, _, _ = self._current_head()
            return {"ok": True, "events": seq, "head": head}

    def append(self, electron_id: str, logical_tick: int, event_type: str, payload):
        with self._lock:
            seq, prev, _, _ = self._current_head()
            body = {
                "schema": "VEC1/EVENT/1",
                "seq": seq + 1,
                "electron_id": electron_id,
                "logical_tick": int(logical_tick),
                "event_type": event_type,
                "payload": payload,
                "prev_hash": prev,
            }
            event = {**body, "event_hash": sha256_text(canonical_json(body))}
            line = canonical_json(event) + "\n"
            with self.path.open("a", encoding="utf-8", newline="\n") as f:
                f.write(line)
                f.flush()
                os.fsync(f.fileno())
            size, mtime = self._fingerprint()
            self._head = (seq + 1, event["event_hash"], size, mtime)
            return event

    def tail(self, limit=200):
        """Return only the requested ledger tail without parsing full history."""
        with self._lock:
            self._current_head()
            try:
                limit = int(limit)
            except (TypeError, ValueError):
                limit = 200
            limit = max(1, min(limit, 1000))
            if not self.path.exists() or self.path.stat().st_size == 0:
                return []
            with self.path.open("rb") as f:
                f.seek(0, os.SEEK_END)
                pos = f.tell()
                chunks = []
                newlines = 0
                block = 64 * 1024
                # Read one extra record when possible because the first chunk can
                # begin in the middle of a UTF-8/JSON line.
                while pos > 0 and newlines < limit + 1:
                    n = min(block, pos)
                    pos -= n
                    f.seek(pos)
                    chunk = f.read(n)
                    chunks.append(chunk)
                    newlines += chunk.count(b"\n")
            data = b"".join(reversed(chunks))
            lines = [line for line in data.splitlines() if line.strip()]
            if pos > 0 and lines:
                lines = lines[1:]  # discard the potentially partial leading line
            out = []
            for raw in lines[-limit:]:
                try:
                    value = strict_json_loads(raw)
                except Exception as e:
                    raise LedgerIntegrityError(f"invalid ledger JSON in tail: {e}") from e
                if not isinstance(value, dict):
                    raise LedgerIntegrityError("ledger tail entry is not an object")
                out.append(value)
            return out
