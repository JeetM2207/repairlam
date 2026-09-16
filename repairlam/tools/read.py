"""Read-only tools. Every output is truncated to protect the context budget."""
import re
from pathlib import Path

MAX_READ_LINES = 120
MAX_MATCHES = 40
MAX_TRACE_HEAD = 40
MAX_TRACE_TAIL = 20


def read_file(workdir, path: str, start: int = 1, end: int = None) -> str:
    """Return numbered lines. Capped at MAX_READ_LINES."""
    p = Path(workdir) / path
    if not p.exists():
        for cand in Path(workdir).rglob(Path(path).name):
            p = cand
            break
        else:
            return f"ERROR: file not found: {path}"

    lines = p.read_text(errors="replace").splitlines()
    total = len(lines)
    start = max(1, start)
    end = total if end is None else min(end, total)
    if end - start + 1 > MAX_READ_LINES:
        end = start + MAX_READ_LINES - 1

    out = [f"{i:5d}| {lines[i-1]}" for i in range(start, end + 1)]
    header = f"# {p.relative_to(workdir)} lines {start}-{end} of {total}"
    if end < total:
        out.append(f"... ({total - end} more lines; call read_file again)")
    return header + "\n" + "\n".join(out)


def search_repo(workdir, pattern: str, glob: str = "*.java") -> str:
    """Literal or regex search across source files."""
    try:
        rx = re.compile(pattern)
    except re.error as e:
        return f"ERROR: bad regex: {e}"

    hits = []
    src = Path(workdir)
    files = sorted(src.rglob(glob),
                   key=lambda f: ("/test/" in str(f), str(f)))
    for f in files:
        s = str(f)
        if "/build/" in s or "/target/" in s or "/classes/" in s:
            continue
        try:
            for i, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
                if rx.search(line):
                    hits.append(f"{f.relative_to(src)}:{i}: {line.strip()[:160]}")
                    if len(hits) >= MAX_MATCHES:
                        break
        except Exception:
            continue
        if len(hits) >= MAX_MATCHES:
            break

    if not hits:
        return f"no matches for: {pattern}"
    note = f"\n... (truncated at {MAX_MATCHES} matches)" if len(hits) >= MAX_MATCHES else ""
    return "\n".join(hits) + note


def truncate_trace(raw: str) -> str:
    """Keep the head and tail of a stack trace, drop the middle."""
    lines = raw.splitlines()
    if len(lines) <= MAX_TRACE_HEAD + MAX_TRACE_TAIL:
        return raw
    head = lines[:MAX_TRACE_HEAD]
    tail = lines[-MAX_TRACE_TAIL:]
    skipped = len(lines) - MAX_TRACE_HEAD - MAX_TRACE_TAIL
    return "\n".join(head + [f"... ({skipped} lines omitted) ..."] + tail)
