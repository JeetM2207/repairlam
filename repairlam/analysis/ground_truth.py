"""Ground-truth method-level localization for Defects4j Lang bugs.

Extracts which method(s) a bug's real fix touches by parsing the changed
line ranges out of the defects4j patch file and mapping them onto method
boundaries (brace-matched) in the real buggy checkout -- not hand-labeled.

IMPORTANT: verified by direct checkout comparison (```defects4j checkout -v
<id>b``` vs ```-v <id>f```) that Lang's .src.patch files are oriented
FIXED -> BUGGY, not BUGGY -> FIXED. Confirmed for bugs 1, 5, and 20. This
module only uses the patch's *line ranges* to find affected methods, which
are direction-independent, so that part is unaffected -- but do not use
this patch file to reason about whether a fix adds or removes code without
accounting for the reversed direction.

Known limitation: the brace-matcher is not string/char-literal aware, so it
can occasionally mis-close a method early or match a declaration-shaped
line inside a comment. This makes the extracted method set occasionally too
generous (an extra spurious name), essentially never too strict -- treat
results as a strong heuristic, not a certified oracle.
"""
import re
import sys
import json
from pathlib import Path

from repairlam.env import d4j

PATCH_DIR = Path.home() / "btp/defects4j/framework/projects/Lang/patches"
DEFAULT_WORKDIR = Path("/tmp/groundtruth_checkouts")

METHOD_DECL_RE = re.compile(
    r'^[ \t]*(?:@\w+(?:\([^)]*\))?\s*)*'
    r'(?:public|protected|private|static|final|synchronized|abstract|native|\s)*'
    r'[\w<>\[\],.\s]+?\s+(?P<name>\w+)\s*\([^)]*\)\s*(?:throws\s+[\w,.\s]+)?\s*\{',
    re.M)
NOT_A_METHOD = {"if", "for", "while", "switch", "catch", "return", "new", "else", "synchronized"}


def method_spans(text):
    """[(start_line, end_line, name), ...] for every method declared in text."""
    spans = []
    for m in METHOD_DECL_RE.finditer(text):
        name = m.group('name')
        if name in NOT_A_METHOD:
            continue
        start_line = text[:m.start()].count('\n') + 1
        brace_pos = m.end() - 1
        depth = 0
        end_pos = None
        for i in range(brace_pos, len(text)):
            c = text[i]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    end_pos = i
                    break
        if end_pos is None:
            continue
        end_line = text[:end_pos].count('\n') + 1
        spans.append((start_line, end_line, name))
    return spans


def parse_hunks(patch_text, target_file):
    """[(old_start, old_len), ...] for hunks touching target_file."""
    hunks = []
    cur_file = None
    for line in patch_text.splitlines():
        if line.startswith('--- a/'):
            cur_file = line[6:]
        elif line.startswith('@@'):
            m = re.match(r'@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@', line)
            if m and cur_file == target_file:
                old_start = int(m.group(1))
                old_len = int(m.group(2) or 1)
                hunks.append((old_start, old_len))
    return hunks


def ground_truth_for_bug(bug, project="Lang", workdir=DEFAULT_WORKDIR):
    """{"file": rel_path, "methods": [name, ...]} for the given bug id, or
    None if the patch/checkout couldn't be read. Reuses a cached checkout
    under workdir/<project>-<bug> across calls."""
    patch_path = PATCH_DIR / f"{bug}.src.patch"
    if not patch_path.exists():
        return None
    patch_text = patch_path.read_text()
    m = re.search(r'^diff --git a/(\S+) b/\S+', patch_text, re.M)
    if not m:
        return None
    rel_path = m.group(1)

    wd = Path(workdir) / f"{project}-{bug}"
    src = wd / rel_path
    if not src.exists():
        if not d4j.checkout(project, bug, str(wd)):
            return None
    if not src.exists():
        return None

    text = src.read_text(errors='replace')
    spans = method_spans(text)
    hunks = parse_hunks(patch_text, rel_path)

    methods = set()
    for old_start, old_len in hunks:
        touched = set(range(old_start, old_start + max(old_len, 1)))
        for s, e, name in spans:
            if touched & set(range(s, e + 1)):
                methods.add(name)
    return {"file": rel_path, "methods": sorted(methods)}


if __name__ == "__main__":
    out = {}
    for b in sys.argv[1:]:
        gt = ground_truth_for_bug(b)
        print(b, "->", gt)
        out[b] = gt
    print(json.dumps(out, indent=2))
