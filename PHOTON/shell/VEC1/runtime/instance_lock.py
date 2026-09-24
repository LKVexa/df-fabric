from __future__ import annotations

import os
from pathlib import Path


class InstanceLockError(RuntimeError):
    pass


class SingleInstanceLock:
    """Cross-platform advisory lock held for one VEC1 reference-shell process.

    The lock file intentionally remains on disk inside runtime_state. Deleting a
    held POSIX lock file can create a second inode and defeat single-instance
    semantics, so ownership is represented by the OS lock, not file existence.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self._fh = None

    def acquire(self):
        if self._fh is not None:
            return self
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fh = self.path.open("a+b")
        try:
            if fh.seek(0, os.SEEK_END) == 0:
                fh.write(b"\0")
                fh.flush()
                os.fsync(fh.fileno())
            fh.seek(0)
            if os.name == "nt":
                import msvcrt
                try:
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError as e:
                    raise InstanceLockError("another VEC1 shell is already using this runtime_state") from e
            else:
                import fcntl
                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as e:
                    raise InstanceLockError("another VEC1 shell is already using this runtime_state") from e
            self._fh = fh
            return self
        except Exception:
            fh.close()
            raise

    def release(self):
        fh, self._fh = self._fh, None
        if fh is None:
            return
        try:
            fh.seek(0)
            if os.name == "nt":
                import msvcrt
                try:
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            else:
                import fcntl
                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass
        finally:
            fh.close()

    def __enter__(self):
        return self.acquire()

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False
