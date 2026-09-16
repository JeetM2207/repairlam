"""Anchored minimal edit. The core operation of the agent.

Never accepts whole-file output. An edit is applied only when its anchor
text matches exactly once, which makes the change auditable and prevents
the model from silently rewriting unrelated code.
"""
from dataclasses import dataclass
from pathlib import Path

MAX_REPLACE_LINES = 100


@dataclass
class EditResult:
    ok: bool
    status: str        # applied | not_found | ambiguous | too_large | no_file
    message: str
    line: int = -1
    occurrences: int = 0


def apply_edit(path, find: str, replace: str) -> EditResult:
    p = Path(path)
    if not p.exists():
        return EditResult(False, "no_file", f"file does not exist: {path}")

    if not find:
        return EditResult(False, "not_found", "find text must not be empty")

    if replace.count("\n") + 1 > MAX_REPLACE_LINES:
        return EditResult(False, "too_large",
                          f"replacement exceeds {MAX_REPLACE_LINES} lines; "
                          "edits must be minimal")

    text = p.read_text()
    n = text.count(find)

    if n == 0:
        return EditResult(False, "not_found",
                          "anchor text not found in file; re-read the file "
                          "and copy the exact text including whitespace",
                          occurrences=0)

    if n > 1:
        return EditResult(False, "ambiguous",
                          f"anchor text appears {n} times; include more "
                          "surrounding context to make it unique",
                          occurrences=n)

    line = text[:text.index(find)].count("\n") + 1
    p.write_text(text.replace(find, replace, 1))
    return EditResult(True, "applied",
                      f"applied 1 edit at line {line}", line=line,
                      occurrences=1)
