import re
"""Tool schemas shown to the model, and the dispatcher that executes them."""
import difflib
import json
from dataclasses import dataclass
from pathlib import Path
from repairlam.tools.edit import apply_edit
from repairlam.tools.read import read_file, search_repo, truncate_trace, list_methods, loose_identifier
from repairlam.env import d4j

READ_HEADER_RE = re.compile(r"^# (.+) lines (\d+)-(\d+) of (\d+)$")
READ_LINE_RE = re.compile(r"^\s*(\d+)\|\s?(.*)$")


@dataclass
class ToolResult:
    status: str        # ok | rejected | error
    output: str


TOOLS = {
    "get_test_output": {
        "desc": "Show the failing test names and the assertion/stack trace "
                "from the most recent test run.",
        "args": {},
    },
    "read_file": {
        "desc": "Read numbered lines from a source file. Max 120 lines per "
                "call. Use start/end to page through a large file.",
        "args": {"path": "str, path relative to repo root",
                 "start": "int, first line (default 1)",
                 "end": "int, last line (optional)"},
    },
    "search_repo": {
        "desc": "Regex search across Java source files. Returns file:line: text. "
                "Use this to locate a method or symbol.",
        "args": {"pattern": "str, regular expression"},
    },
    "identify_bug_method": {
        "desc": "State the exact method name you believe contains the bug. "
                "Checked against the codebase; required to leave COLLECT.",
        "args": {"method_name": "str, exact method name, e.g. 'createNumber'"},
    },
    "apply_edit": {
        "desc": "Replace an exact snippet of text in a file. The 'find' text "
                "must appear EXACTLY ONCE, copied verbatim including "
                "whitespace. Keep edits minimal; never paste a whole file.",
        "args": {"path": "str, path relative to repo root",
                 "find": "str, exact existing text",
                 "replace": "str, replacement text"},
    },
    "run_tests": {
        "desc": "Compile the project and run the test suite. Slow; use only "
                "after making an edit.",
        "args": {},
    },
    "finish": {
        "desc": "Declare the bug fixed. Only call after run_tests reports "
                "all tests passing.",
        "args": {},
    },
    "escalate": {
        "desc": "Stop and ask a human one specific, answerable question. Use "
                "when repeated attempts fail for the same reason.",
        "args": {"reason": "str, what you tried and why it failed",
                 "question": "str, one specific question"},
    },
}


def tools_doc(exclude=()) -> str:
    """Render the tool list for the system prompt.

    `exclude` keeps a tool out of the shared system prompt entirely (used
    for state-specific tools whose schema is instead folded into that
    state's own user-message prompt) -- the system prompt is sent on every
    turn regardless of state, and at temperature=0 even a small, unrelated
    addition to it can shift greedy decoding in states that never use the
    new tool at all. Keeping it out of the always-on system prompt confines
    its blast radius to the one state that actually needs it.
    """
    out = []
    for name, spec in TOOLS.items():
        if name in exclude:
            continue
        args = ", ".join(f"{k} ({v})" for k, v in spec["args"].items()) or "none"
        out.append(f"- {name}\n    {spec['desc']}\n    args: {args}")
    return "\n".join(out)


class Dispatcher:
    """Executes a tool call against one bug's workspace."""

    def __init__(self, workdir, log=None, bug_id=None, trigger_class=None,
                 hint_file=None, env=None, source_glob="*.java",
                 test_file_suffixes=("Test.java",)):
        self.workdir = str(workdir)
        self.log = log
        self.bug_id = bug_id
        self.trigger_class = trigger_class
        self.hint_file = hint_file
        # env supplies compile_project(workdir) and run_tests(workdir,
        # timeout=..., test_class=None) -> TestResult. Defaults to the
        # Defects4j backend so every existing caller keeps working
        # unchanged; repairlam/github injects a generic git+shell backend.
        self.env = env if env is not None else d4j
        # source_glob/test_file_suffixes default to the Java/Defects4j
        # shape; repairlam/github overrides both per-repo since a live
        # repo can be in any language.
        self.source_glob = source_glob
        self.test_file_suffixes = tuple(test_file_suffixes)
        self.last_test = None
        self.edits = []
        self.reads = []   # [{"path": str, "start": int, "lines": [str, ...]}]

    def call(self, tool: str, args: dict) -> ToolResult:
        if tool not in TOOLS:
            return ToolResult("error",
                              f"unknown tool '{tool}'. Available: "
                              + ", ".join(TOOLS))
        try:
            return getattr(self, f"_{tool}")(args)
        except Exception as e:
            return ToolResult("error", f"{type(e).__name__}: {str(e)[:300]}")

    # --- tools ---

    def _get_test_output(self, a):
        if self.last_test is None:
            self.last_test = self.env.run_tests(self.workdir)
        t = self.last_test
        if t.passed:
            return ToolResult("ok", "All tests pass.")
        names = "\n".join(f"  - {n}" for n in t.failing[:5])
        return ToolResult("ok",
                          f"Failing tests ({len(t.failing)}):\n{names}\n\n"
                          f"{truncate_trace(t.raw)}")

    def _read_file(self, a):
        out = read_file(self.workdir, a["path"], int(a.get("start", 1)),
                        int(a["end"]) if a.get("end") else None)
        self._record_read(out)
        return ToolResult("ok", out)

    def _record_read(self, out):
        """Store the literal lines returned by read_file so a later
        not_found apply_edit can be shown real text to copy from."""
        lines = out.splitlines()
        if not lines:
            return
        m = READ_HEADER_RE.match(lines[0])
        if not m:
            return
        path, start = m.group(1), int(m.group(2))
        content = []
        for ln in lines[1:]:
            lm = READ_LINE_RE.match(ln)
            if lm:
                content.append(lm.group(2))
        if content:
            self.reads.append({"path": path, "start": start, "lines": content})

    def _closest_match(self, find):
        """Fuzzy-match `find` against every line window seen via read_file
        this run. Returns a real snippet (path + line) to show the model,
        or None if nothing was ever read."""
        find_lines = find.splitlines() or [find]
        k = len(find_lines)
        candidates = []   # (window_text, path, line_no)
        for r in self.reads:
            lines = r["lines"]
            for i in range(max(1, len(lines) - k + 1)):
                window = lines[i:i + k]
                candidates.append(("\n".join(window), r["path"], r["start"] + i))
        if not candidates:
            return None
        texts = [c[0] for c in candidates]
        best = difflib.get_close_matches(find, texts, n=1, cutoff=0.3)
        if not best:
            return None
        path, line_no = next((p, l) for t, p, l in candidates if t == best[0])
        return (f"Closest real text found in {path} near line {line_no} -- "
                f"copy the find text from here instead of guessing again:\n"
                f"{best[0]}")

    def _search_repo(self, a):
        return ToolResult("ok", search_repo(self.workdir, a["pattern"],
                                            glob=self.source_glob,
                                            hint_file=self.hint_file))

    # Java declaration syntax specifically (keyword modifiers before the
    # name). repairlam/github currently only targets Java repos for the
    # same reason -- generalizing this to other languages' declaration
    # syntax is follow-up work, not yet done.
    _DECL_TEMPLATE = (r"(?:public|private|protected|static|final|abstract|"
                       r"synchronized)\b[^;{{}}]*\b{name}\s*\(")

    def _identify_bug_method(self, a):
        name = (a.get("method_name") or "").strip()
        if not re.match(r"^[A-Za-z_]\w*$", name):
            return ToolResult("rejected",
                              "method_name must be a single valid Java "
                              "identifier, e.g. 'createNumber' -- not a "
                              "sentence, path, or signature.")
        pat = re.compile(self._DECL_TEMPLATE.format(name=re.escape(name)))
        found = []
        for f in Path(self.workdir).rglob(self.source_glob):
            s = str(f)
            if "/test/" in s or "/build/" in s or "/target/" in s or "/classes/" in s:
                continue
            try:
                text = f.read_text(errors="replace")
            except Exception:
                continue
            if pat.search(text):
                found.append(str(f.relative_to(self.workdir)))
        if found:
            where = ", ".join(found[:3])
            return ToolResult("ok",
                              f"Confirmed: '{name}' is declared in {where}. "
                              "You may now proceed to TRY_FIX with this as "
                              "your target method.")
        return ToolResult("rejected",
                          f"'{name}' is not declared as a method anywhere in "
                          "the source tree. This is likely a hallucinated or "
                          "misspelled name -- it does NOT exist. Read more of "
                          "the source file or use search_repo to find the "
                          "real method name, then try identify_bug_method "
                          "again. You cannot proceed to TRY_FIX until this "
                          "succeeds.")

    def force_identify_method(self, last_search_pattern=None, last_read_path=None):
        """Called by the FSM when COLLECT has run too long without a
        committed method. Derives a best-guess name from whatever the model
        was last searching for or reading (never invents one), validates it
        the same way identify_bug_method does, and returns
        (candidate_name_or_None, ToolResult)."""
        candidate = None
        if last_search_pattern:
            candidate = loose_identifier(last_search_pattern)
        if not candidate and last_read_path:
            for r in reversed(self.reads):
                if r["path"] == last_read_path:
                    text = "\n".join(r["lines"])
                    found = list_methods(text, limit=1)
                    if found:
                        candidate = found[0].split(": ", 1)[1]
                    break
        if not candidate:
            return None, ToolResult("rejected",
                                    "no candidate method name could be derived "
                                    "from anything searched or read this run")
        return candidate, self._identify_bug_method({"method_name": candidate})

    def _apply_edit(self, a):
        if "/test/" in a["path"] or a["path"].endswith(self.test_file_suffixes):
            return ToolResult("rejected",
                              "editing test files is not allowed; fix the "
                              "source code instead")
        find = re.sub(r"^\s*\d+\|\s?", "", a["find"], flags=re.M)
        repl = re.sub(r"^\s*\d+\|\s?", "", a["replace"], flags=re.M)
        r = apply_edit(f"{self.workdir}/{a['path']}", find, repl)
        if not r.ok:
            msg = r.message
            if r.status == "not_found":
                suggestion = self._closest_match(find)
                if suggestion:
                    msg += "\n\n" + suggestion
            return ToolResult("rejected", msg)
        self.edits.append({"path": a["path"], "line": r.line,
                           "find": a["find"], "replace": a["replace"]})
        self.last_test = None          # results are now stale
        return ToolResult("ok", r.message)

    def _run_tests(self, a):
        ok, out = self.env.compile_project(self.workdir)
        if not ok:
            self.last_test = None
            return ToolResult("ok", f"COMPILE FAILED\n{truncate_trace(out)}")
        t = self.env.run_tests(self.workdir, timeout=180, test_class=self.trigger_class)
        self.last_test = t
        if t.passed:
            msg = ("TRIGGER TEST PASSES (only the failing test class was run; "
                   "a full-suite check happens automatically before finish)"
                   if self.trigger_class else "ALL TESTS PASS")
            return ToolResult("ok", msg)
        names = "\n".join(f"  - {n}" for n in t.failing[:5])
        return ToolResult("ok",
                          f"STILL FAILING ({len(t.failing)}):\n{names}\n\n"
                          f"{truncate_trace(t.raw)}")

    def _finish(self, a):
        return ToolResult("ok", "FINISH")

    def _escalate(self, a):
        return ToolResult("ok",
                          f"ESCALATE\nreason: {a.get('reason','')}\n"
                          f"question: {a.get('question','')}")
