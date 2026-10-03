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
QUALITY_CHECKS = {"project", "governance", "debug", "release", "runner", "handoff"}


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


def strict_json(text: str):
    """Reject ambiguous keys and both spellings of non-finite JSON numbers."""
    def bad(value):
        raise ValueError(f"Non-finite JSON constant: {value}")
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError(f"Duplicate JSON key: {key}")
            value[key] = item
        return value
    def real(text):
        import math
        value = float(text)
        if not math.isfinite(value):
            raise ValueError("Non-finite JSON number")
        return value
    def integer(text):
        import math
        value=int(text)
        try: finite=math.isfinite(value)
        except OverflowError: finite=False
        if not finite: raise ValueError('JSON integer exceeds finite numeric range')
        return value
    return json.loads(text, parse_constant=bad, parse_float=real, parse_int=integer, object_pairs_hook=pairs)


def read_json(path: Path):
    return strict_json(path.read_text(encoding="utf-8-sig"))


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
    protected = read_json(root/'project/policy.json').get('archive_prefixes',[]) if (root/'project/policy.json').is_file() else []
    protected = tuple(protected) + ('results/validation/','data/thermo/','tests/reference/cea/raw/')
    text_suffixes={'.md','.py','.ps1','.c','.h','.json','.yml','.yaml','.txt','.ini','.tsv','.svg','.html','.mmd'}
    pairs = []
    for path in project_files(root):
        rel = path.relative_to(root).as_posix()
        if rel in DYNAMIC_PATHS or rel.startswith(("taskshot/", "project/evidence/")):
            continue
        if path.suffix.lower() == ".pyc":
            continue
        # Only editable text receives an EOL-independent identity. Byte archives do not.
        if not rel.startswith(protected) and path.suffix.lower() in text_suffixes:
            identity=hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
        else:
            identity=digest(path)
        pairs.append((rel, identity))
    return hashlib.sha256(canonical(pairs)).hexdigest()


def git(root: Path, *arguments: str, check=False) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "core.quotepath=false", *arguments], cwd=root,
                          capture_output=True, encoding="utf-8", errors="replace", check=check)
