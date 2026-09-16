"""Tool schemas shown to the model, and the dispatcher that executes them."""
import json
from dataclasses import dataclass
from repairlam.tools.edit import apply_edit
from repairlam.tools.read import read_file, search_repo, truncate_trace
from repairlam.env import d4j


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


def tools_doc() -> str:
    """Render the tool list for the system prompt."""
    out = []
    for name, spec in TOOLS.items():
        args = ", ".join(f"{k} ({v})" for k, v in spec["args"].items()) or "none"
        out.append(f"- {name}\n    {spec['desc']}\n    args: {args}")
    return "\n".join(out)


class Dispatcher:
    """Executes a tool call against one bug's workspace."""

    def __init__(self, workdir, log=None, bug_id=None):
        self.workdir = str(workdir)
        self.log = log
        self.bug_id = bug_id
        self.last_test = None
        self.edits = []

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
            self.last_test = d4j.run_tests(self.workdir)
        t = self.last_test
        if t.passed:
            return ToolResult("ok", "All tests pass.")
        names = "\n".join(f"  - {n}" for n in t.failing[:5])
        return ToolResult("ok",
                          f"Failing tests ({len(t.failing)}):\n{names}\n\n"
                          f"{truncate_trace(t.raw)}")

    def _read_file(self, a):
        return ToolResult("ok", read_file(self.workdir, a["path"],
                                          int(a.get("start", 1)),
                                          int(a["end"]) if a.get("end") else None))

    def _search_repo(self, a):
        return ToolResult("ok", search_repo(self.workdir, a["pattern"]))

    def _apply_edit(self, a):
        r = apply_edit(f"{self.workdir}/{a['path']}", a["find"], a["replace"])
        if not r.ok:
            return ToolResult("rejected", r.message)
        self.edits.append({"path": a["path"], "line": r.line,
                           "find": a["find"], "replace": a["replace"]})
        self.last_test = None          # results are now stale
        return ToolResult("ok", r.message)

    def _run_tests(self, a):
        ok, out = d4j.compile_project(self.workdir)
        if not ok:
            self.last_test = None
            return ToolResult("ok", f"COMPILE FAILED\n{truncate_trace(out)}")
        t = d4j.run_tests(self.workdir)
        self.last_test = t
        if t.passed:
            return ToolResult("ok", "ALL TESTS PASS")
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
