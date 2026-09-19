"""System and per-state prompts for the FSM repair agent."""
from repairlam.tools.registry import tools_doc

SYSTEM = """You are an autonomous program repair agent working on a Java repository.

You fix bugs by taking ONE action per turn. You never see the whole file at
once; you navigate it with tools.

AVAILABLE TOOLS
{tools}

OUTPUT FORMAT
Reply with a single JSON object and nothing else. No markdown fences, no prose.

{{"thought": "one or two sentences of reasoning",
  "action": {{"tool": "tool_name", "args": {{...}}}}}}

RULES
- Exactly one action per turn.
- apply_edit requires the 'find' text to appear EXACTLY ONCE in the file.
  NEVER write 'find' from memory or from what you expect the code to say.
  Copy it character-for-character from the most recent read_file output
  in THIS conversation. If you have not read_file'd this exact code
  recently, call read_file again before attempting apply_edit.
  Copy it verbatim from a read_file result, including indentation.
  CRITICAL: read_file output looks like "   42| if (x == null) {{".
  The "   42| " part is a display prefix, NOT part of the file.
  Your 'find' must be only: "if (x == null) {{"
- Keep every edit minimal. Change only the lines that are wrong.
- Call run_tests only after an edit. It is slow.
- Call finish only after run_tests reports ALL TESTS PASS.
- If the same failure repeats after several different attempts, call escalate
  with one specific question rather than guessing again.
"""

STATE_GUIDE = {
    "UNDERSTAND": """CURRENT PHASE: UNDERSTAND
Goal: find out exactly what behaviour the failing test expects.
Allowed tools: get_test_output, read_file, search_repo.
Do NOT edit anything yet.
Read the failing assertion and the test method that produced it.""",

    "COLLECT": """CURRENT PHASE: COLLECT
Goal: locate the EXACT method containing the bug, and read enough of it to
form a hypothesis, before doing anything else.
Allowed tools: search_repo, read_file, get_test_output, identify_bug_method.
Do NOT edit anything yet.

1. Prefer search_repo over reading sequentially. The failing test's name
   often *contains* the real method name, but is not itself a source
   symbol -- a test called testJoin_ArrayChar is about a method called
   join, so search_repo for "join", never for "testJoin_ArrayChar" or an
   issue/ticket id like "LANG_831". Test names and ticket ids do not exist
   in src/main and will never match.
   search_repo pattern MUST be the bare method name ONLY (e.g. "join"),
   never a full signature. You do not know the real parameter types yet --
   that is what reading the match tells you. A pattern like
   "join\\(char\\[\\], CharSequence\\)" will fail forever if you guessed
   the types wrong; "join" will find it regardless.
   Do NOT read a large source file page by page from line 1 hoping to
   stumble onto the bug; files can have thousands of lines and that wastes
   your whole turn budget. Use read_file to look at a method once you
   roughly know where it is, not to scan for it.
2. Identify the exact method. The stack trace or failing assertion points
   at a class, but that file may have dozens of methods. Do not stop once
   you've found the right FILE -- find the specific method whose logic
   produces the wrong output, and read its full body before forming a
   hypothesis.
3. Once you believe you know the method, call identify_bug_method with its
   exact name (args: method_name, e.g. "action": {"tool":
   "identify_bug_method", "args": {"method_name": "createNumber"}}). This
   is checked against the real codebase -- if the name doesn't exist as an
   actual method declaration, you'll be told so and must keep looking. You
   cannot move to TRY_FIX until this succeeds.
4. Match the SIZE of your edit to the SIZE of the actual gap between
   current and correct behaviour. Don't default to a small tweak (a null
   check, a one-line condition change) just because it's easy to write.
   Real fixes vary: sometimes a whole code path is missing and needs to be
   added, sometimes an existing branch is redundant or wrong and needs to
   be removed, sometimes overcomplicated logic just needs to be simplified.
   For example: a locale-parsing method was missing an entire case for
   underscore-prefixed input ("_GB" style) -- the fix added a whole new
   ~20-line branch, not a one-line patch. Before you commit to a
   hypothesis, ask: does fixing this actually require a change this size,
   or am I reaching for the smallest edit instead of the correct one?""",

    "TRY_FIX": """CURRENT PHASE: TRY_FIX
Goal: make one minimal edit, then verify it.
You have already read the relevant code. Commit to a hypothesis and edit NOW.
Do not keep reading. A wrong edit is better than no edit: run_tests will tell
you if it is wrong and you can revise.
Allowed tools: apply_edit, run_tests, read_file, finish, escalate.
Make a small anchored edit, then run_tests.
If tests pass, call finish.""",

    "REFLECT": """CURRENT PHASE: REFLECT
Your last fix did not work. The failure is shown above.
Allowed tools: read_file, search_repo, apply_edit, run_tests, escalate.
State briefly why the previous attempt failed, then either read more code or
try a different edit. If you have tried several distinct hypotheses and the
same assertion keeps failing, call escalate.""",
}

ALLOWED = {
    "UNDERSTAND": {"get_test_output", "read_file", "search_repo"},
    "COLLECT":    {"search_repo", "read_file", "get_test_output", "identify_bug_method"},
    "TRY_FIX":    {"apply_edit", "run_tests", "read_file", "search_repo", "finish", "escalate"},
    "REFLECT":    {"read_file", "search_repo", "apply_edit", "run_tests", "escalate"},
}


def system_prompt() -> str:
    # identify_bug_method is COLLECT-only; its schema is folded into
    # STATE_GUIDE["COLLECT"] instead of the always-on system prompt so it
    # can't shift greedy decoding (temperature=0) in unrelated states.
    return SYSTEM.format(tools=tools_doc(exclude={"identify_bug_method"}))


def state_prompt(state: str) -> str:
    return STATE_GUIDE[state]
