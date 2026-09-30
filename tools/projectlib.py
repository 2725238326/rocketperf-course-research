"""Shared, standard-library-only project governance primitives."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRS = {".git", "build", "__pycache__", ".venv", "node_modules", ".locks"}
DYNAMIC_PATHS = {"project/tasks.json", "worknow.md", "docs/tasks.md"}
QUALITY_CHECKS = {"project", "governance", "debug", "release", "runner"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def subprocess_env():
    environment=os.environ.copy()
    environment['PYTHONUTF8']='1'
    environment['PYTHONIOENCODING']='utf-8'
    return environment


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def local_path(root: Path, relative: str) -> Path:
    """Refuse absolute paths, traversal and links escaping the project."""
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("Use a nonempty project-relative forward-slash path")
    candidate = Path(relative)
    if candidate.is_absolute() or ":" in relative or ".." in candidate.parts:
        raise ValueError(f"Unsafe project path: {relative}")
    resolved = (root / candidate).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"Project path escapes root: {relative}")
    return resolved


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, prefix=".writing-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()  # Only this function's unique temporary file.


def atomic_json(path: Path, value) -> None:
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


@contextmanager
def lock(root: Path, name="tasks"):
    """OS-released advisory lock; process crashes cannot leave a stale lock."""
    folder = root / "project/.locks"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / f"{name}.lock").open("a+b") as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        acquired = False
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
            yield
        except OSError as exc:
            if not acquired:
                raise ValueError("Another process owns the project state lock; retry after it finishes") from exc
            raise
        finally:
            if acquired:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def project_files(root: Path):
    for folder, directories, filenames in os.walk(root):
        relative = Path(folder).relative_to(root)
        directories[:] = sorted(d for d in directories if d not in IGNORED_DIRS
                                and not (relative == Path("results") and d == "local"))
        for name in sorted(filenames):
            if name.startswith('.writing-'): continue
            path = Path(folder) / name
            if not path.is_symlink():
                yield path


def fingerprint(root: Path) -> str:
    """Quality input identity; excludes state/history/output to avoid self-reference.

    Raw evidence is included so post-check archive changes invalidate acceptance.
    """
    pairs = []
    for path in project_files(root):
        rel = path.relative_to(root).as_posix()
        if rel in DYNAMIC_PATHS or rel.startswith(("taskshot/", "project/evidence/")):
            continue
        if path.suffix.lower() == ".pyc":
            continue
        pairs.append((rel, digest(path)))
    return hashlib.sha256(canonical(pairs)).hexdigest()


def git(root: Path, *arguments: str, check=False) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "core.quotepath=false", *arguments], cwd=root,
                          capture_output=True, encoding="utf-8", errors="replace", check=check)
