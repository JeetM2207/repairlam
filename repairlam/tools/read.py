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


def _run_search(workdir, rx, glob):
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
    return hits


def _format_hits(hits):
    note = f"\n... (truncated at {MAX_MATCHES} matches)" if len(hits) >= MAX_MATCHES else ""
    return "\n".join(hits) + note


def _loose_identifier(pattern):
    """Best-effort extraction of a bare method/identifier name from a
    signature-shaped search pattern, for a fallback retry on zero hits."""
    m = re.search(r"([A-Za-z_]\w*)\s*\\?\(", pattern)
    if m:
        return m.group(1)
    idents = re.findall(r"[A-Za-z_]\w*", pattern)
    return max(idents, key=len) if idents else None


_METHOD_DECL_RE = re.compile(
    r"^\s*(?:@\w+(?:\([^)]*\))?\s*)*"
    r"(?:public|protected|private|static|final|synchronized|abstract|native|\s)*"
    r"[\w<>\[\],.\s]+?\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w,.\s]+)?\s*[{;]",
    re.M)
_NOT_A_METHOD = {"if", "for", "while", "switch", "catch", "return", "new", "else"}


def list_methods(text, limit=30):
    """Real method names actually declared in `text`, in source order --
    used as a concrete fallback when a search pattern finds nothing."""
    out = []
    for m in _METHOD_DECL_RE.finditer(text):
        name = m.group(1)
        if name in _NOT_A_METHOD:
            continue
        line = text[:m.start()].count("\n") + 1
        out.append(f"{line}: {name}")
        if len(out) >= limit:
            break
    return out


def search_repo(workdir, pattern: str, glob: str = "*.java", hint_file: str = None) -> str:
    """Literal or regex search across source files. On zero matches, retries
    with a bare identifier extracted from the pattern; if that also finds
    nothing, lists real method names from hint_file so the model has
    something concrete to act on instead of guessing another pattern blind."""
    try:
        rx = re.compile(pattern)
    except re.error as e:
        return f"ERROR: bad regex: {e}"

    hits = _run_search(workdir, rx, glob)
    if hits:
        return _format_hits(hits)

    loose = _loose_identifier(pattern)
    if loose and loose != pattern:
        try:
            loose_hits = _run_search(workdir, re.compile(re.escape(loose)), glob)
        except re.error:
            loose_hits = []
        if loose_hits:
            return (f"no matches for '{pattern}'; retried with just the "
                    f"identifier '{loose}' instead:\n" + _format_hits(loose_hits))

    if hint_file:
        p = Path(workdir) / hint_file
        if p.exists():
            methods = list_methods(p.read_text(errors="replace"))
            if methods:
                return (f"no matches found for '{pattern}' (even loosened to "
                        f"'{loose}'). Showing methods actually in {hint_file} "
                        f"instead -- pick the real name from this list:\n"
                        + "\n".join(methods))

    return f"no matches for: {pattern}"


def truncate_trace(raw: str) -> str:
    """Keep the head and tail of a stack trace, drop the middle."""
    lines = raw.splitlines()
    if len(lines) <= MAX_TRACE_HEAD + MAX_TRACE_TAIL:
        return raw
    head = lines[:MAX_TRACE_HEAD]
    tail = lines[-MAX_TRACE_TAIL:]
    skipped = len(lines) - MAX_TRACE_HEAD - MAX_TRACE_TAIL
    return "\n".join(head + [f"... ({skipped} lines omitted) ..."] + tail)
