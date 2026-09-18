"""FSM repair agent. One action per turn, anchored edits, logged throughout."""
import os, re, sys, json, time, argparse, requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from repairlam.events import EventLog
from repairlam.env import d4j
from repairlam.tools.registry import Dispatcher
from repairlam.agent.prompts import system_prompt, state_prompt, ALLOWED

BASE_URL = os.getenv("BASE_URL", "http://localhost:8603/v1")
MODEL = os.getenv("MODEL", "qwen32b")
BTP = os.path.expanduser("~/btp")
WORK = f"{BTP}/repairlam/workspaces"
LOGS = f"{BTP}/repairlam/logs"
RESULTS = f"{BTP}/repairlam/results"

MAX_TURNS = 30
MAX_FIX_ATTEMPTS = 5
KEEP_RECENT = 6          # verbatim history turns before summarising
SAFETY = 800


def server_ctx():
    r = requests.get(f"{BASE_URL}/models", timeout=30)
    return int(r.json()["data"][0]["max_model_len"])


def est(text):
    return int(len(text) / 2.8) + 1


def ask(messages, max_tokens):
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/chat/completions", timeout=900, json={
        "model": MODEL, "messages": messages,
        "max_tokens": max_tokens, "temperature": 0.0,
    })
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    d = r.json()
    return (d["choices"][0]["message"]["content"],
            d["usage"]["prompt_tokens"], d["usage"]["completion_tokens"],
            int((time.time() - t0) * 1000))


def _repair_json(t):
    """Fix the two most common ways models break JSON when embedding code:
    literal newlines inside a string value, and unescaped double quotes."""
    out = []
    in_str = False
    i = 0
    while i < len(t):
        c = t[i]
        if c == '"' and (i == 0 or t[i-1] != "\\"):
            in_str = not in_str
            out.append(c)
        elif in_str and c == "\n":
            out.append("\\n")
        elif in_str and c == "\t":
            out.append("\\t")
        else:
            out.append(c)
        i += 1
    return "".join(out)


def parse_action(text):
    """Extract {thought, action} from the model reply. Tolerant of fences
    and of the model embedding raw newlines/quotes inside JSON strings."""
    t = text.strip()
    if "```" in t:
        m = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
        if m:
            t = m.group(1).strip()
    decoder = json.JSONDecoder()
    obj, last_err = None, "no JSON object found"
    for candidate in (t, _repair_json(t)):
        i = candidate.find("{")
        if i == -1:
            continue
        try:
            obj, _ = decoder.raw_decode(candidate, i)
            break
        except json.JSONDecodeError as e:
            last_err = e
    if obj is None:
        return None, None, (f"invalid JSON: {last_err}"
                             if isinstance(last_err, json.JSONDecodeError) else last_err)

    act = obj.get("action") or {}
    tool = act.get("tool")
    if not tool:
        return None, None, "missing action.tool"
    return obj.get("thought", ""), {"tool": tool, "args": act.get("args") or {}}, None


def next_state(state, tool, result, attempts):
    if tool == "finish":
        return "DONE"
    if tool == "escalate":
        return "ESCALATE"
    if state == "UNDERSTAND" and tool == "read_file":
        return "COLLECT"
    if state == "COLLECT" and tool in ("read_file", "search_repo"):
        return "TRY_FIX"
    if tool == "run_tests":
        if "ALL TESTS PASS" in result.output:
            return "TRY_FIX"        # model should now call finish
        if attempts >= MAX_FIX_ATTEMPTS:
            return "ESCALATE"
        return "REFLECT"
    if state == "REFLECT" and tool == "apply_edit":
        return "TRY_FIX"
    return state


def run_bug(project, bug, ctx, results):
    bug_id = f"{project}-{bug}"
    run_id = f"{bug_id}_{MODEL}_fsm_{time.strftime('%Y%m%dT%H%M%S')}"
    log = EventLog(run_id, LOGS)
    wd = f"{WORK}/{bug_id}"
    print(f"\n=== {bug_id} ===", flush=True)

    try:
        if not d4j.checkout(project, bug, wd):
            log.summary(bug_id, "ERROR", model=MODEL, note="checkout failed")
            print("  ERROR checkout"); return "ERROR"
        ok, _ = d4j.compile_project(wd)
        if not ok:
            log.summary(bug_id, "ERROR", model=MODEL, note="compile failed")
            print("  ERROR compile"); return "ERROR"

        initial = d4j.run_tests(wd, timeout=600)
        trigger_class = (initial.failing[0].split("::")[0]
                         if initial.failing else None)
        disp = Dispatcher(wd, log, bug_id, trigger_class=trigger_class)
        disp.last_test = initial
        try:
            hint_file = str(d4j.buggy_file(wd).relative_to(wd))
        except Exception:
            hint_file = None
        sysmsg = system_prompt()
        history = []
        state, attempts, outcome = "UNDERSTAND", 0, "FAILED"
        reads_since_edit = 0
        files_read = {}
        escalation = None

        turn = 0
        while turn < MAX_TURNS:
            turn += 1
            recent = history[-KEEP_RECENT:]
            older = len(history) - len(recent)
            note = (f"[{older} earlier turns omitted]\n" if older > 0 else "")
            convo = note + "\n".join(recent)

            hint = (f"The defect is in: {hint_file}\n\n" if hint_file else "")
            allowed = set(ALLOWED[state])
            if reads_since_edit > 3 and state in ("TRY_FIX", "REFLECT"):
                allowed -= {"read_file", "search_repo", "get_test_output"}
            if history and history[-1].startswith("[system] Edit applied"):
                allowed = {"run_tests"}
            urgent = ("\nYOU HAVE READ ENOUGH. You must call apply_edit now "
                      "with your best hypothesis, or escalate.\n"
                      if reads_since_edit > 3 else "")
            user = (hint + f"{state_prompt(state)}{urgent}\n\n"
                    f"Allowed tools this phase: {', '.join(sorted(allowed))}\n\n"
                    f"--- history ---\n{convo}\n--- end history ---\n\n"
                    f"Turn {turn}/{MAX_TURNS}. Reply with one JSON action.")

            msgs = [{"role": "system", "content": sysmsg},
                    {"role": "user", "content": user}]
            budget = ctx - est(sysmsg + user) - SAFETY
            if budget < 300:
                history = history[-2:]
                continue

            text, ti, to, ms = ask(msgs, min(700, budget))
            thought, action, err = parse_action(text)

            if err:
                history.append(f"[you] {text[:200]}\n[system] PARSE ERROR: {err}. "
                               "Reply with only a JSON object.")
                log.event(bug_id, state, thought=None, tool=None,
                          result_status="parse_error", result_summary=err,
                          tokens_in=ti, tokens_out=to, latency_ms=ms, model=MODEL)
                print(f"  {turn} {state} parse_error", flush=True)
                continue

            tool, args = action["tool"], action["args"]

            if tool in ("read_file", "search_repo") and state in ("TRY_FIX", "REFLECT"):
                reads_since_edit += 1
                if reads_since_edit > 10:
                    state = "ESCALATE"
                    outcome = "ESCALATED"
                    escalation = "read limit exceeded without any edit attempt"
                    print(f"  {turn} forced escalate (read limit)", flush=True)
                    break
                if reads_since_edit > 3:
                    msg = ("BLOCKED: you already read enough. Your next action "
                           "MUST be apply_edit or escalate. Reading is disabled.")
                    history.append(f"[you] tried {tool}\n[system] {msg}")
                    log.event(bug_id, state, thought=thought, tool=tool,
                              result_status="blocked", result_summary=msg,
                              tokens_in=ti, tokens_out=to, latency_ms=ms,
                              model=MODEL)
                    print(f"  {turn} {state} read-limit", flush=True)
                    turn -= 1
                    continue
            if tool not in ALLOWED[state]:
                msg = (f"'{tool}' is not allowed in {state}. "
                       f"Allowed: {', '.join(sorted(ALLOWED[state]))}")
                history.append(f"[you] {tool}\n[system] {msg}")
                log.event(bug_id, state, thought=thought, tool=tool, args=args,
                          result_status="blocked", result_summary=msg,
                          tokens_in=ti, tokens_out=to, latency_ms=ms, model=MODEL)
                print(f"  {turn} {state} blocked {tool}", flush=True)
                continue

            res = disp.call(tool, args)
            if tool == "apply_edit" and res.status == "ok":
                attempts += 1
                reads_since_edit = 0
            elif tool == "run_tests":
                reads_since_edit = 0

            reread_path = None
            if tool == "read_file":
                reread_path = args.get("path")
                if reread_path:
                    files_read[reread_path] = files_read.get(reread_path, 0) + 1

            log.event(bug_id, state, thought=thought, tool=tool,
                      args={k: str(v)[:200] for k, v in args.items()},
                      result_status=res.status,
                      result_summary=res.output[:300],
                      tokens_in=ti, tokens_out=to, latency_ms=ms, model=MODEL)
            print(f"  {turn} {state:10s} {tool:16s} {res.status}", flush=True)

            history.append(f"[you] {thought}\n[action] {tool} {json.dumps(args)[:300]}\n"
                           f"[result:{res.status}] {res.output[:1200]}")
            if tool == "apply_edit" and res.status == "ok":
                history.append("[system] Edit applied. You MUST call run_tests "
                               "as your very next action before doing anything else.")
            if reread_path and files_read.get(reread_path, 0) >= 2:
                history.append(f"[system] You already read {reread_path}. Now read "
                               "the SOURCE file (not the test file) where the buggy "
                               "method is defined.")

            if tool == "finish":
                t = d4j.run_tests(wd)
                outcome = "PLAUSIBLE" if t.passed else "FAILED"
                break
            if tool == "escalate" and attempts < 2:
                history.append("[system] REJECTED: fewer than 2 fix attempts made. Try a different edit first.")
                print(f"  {turn} {state} escalate-too-early", flush=True)
                state = "TRY_FIX"
                reads_since_edit = 0
                continue
            if tool == "escalate":
                outcome = "ESCALATED"
                escalation = res.output
                break

            state = next_state(state, tool, res, attempts)
            if state == "ESCALATE":
                outcome = "ESCALATED"
                break
        else:
            outcome = "TIMEOUT"

        if outcome in ("FAILED", "TIMEOUT"):
            t = d4j.run_tests(wd)
            if t.passed:
                outcome = "PLAUSIBLE"

        s = log.summary(bug_id, outcome, model=MODEL,
                        edits_applied=len(disp.edits),
                        fix_attempts=attempts,
                        escalation=escalation)
        print(f"  -> {outcome} ({len(disp.edits)} edits)", flush=True)
        results.append(s)
        return outcome

    except Exception as e:
        log.summary(bug_id, "ERROR", model=MODEL, note=str(e)[:300])
        print(f"  -> ERROR {str(e)[:200]}", flush=True)
        return "ERROR"
    finally:
        d4j.cleanup(wd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="Lang")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--only", default=None, help="comma-separated bug ids")
    a = ap.parse_args()

    Path(RESULTS).mkdir(parents=True, exist_ok=True)
    Path(WORK).mkdir(parents=True, exist_ok=True)

    ctx = server_ctx()
    print(f"server context: {ctx}")

    bugs = (a.only.split(",") if a.only
            else d4j.active_bugs(a.project)[:a.n])
    print(f"FSM agent on {len(bugs)} {a.project} bugs with {MODEL}")

    results, counts = [], {}
    for b in bugs:
        o = run_bug(a.project, b, ctx, results)
        counts[o] = counts.get(o, 0) + 1

    out = Path(RESULTS) / f"phase2_fsm_{a.project}_{MODEL}.json"
    out.write_text(json.dumps({"context": ctx, "counts": counts,
                               "runs": results}, indent=2))
    print("\n" + "=" * 40)
    for k, v in sorted(counts.items()):
        print(f"{k:12s} {v}")
    n = sum(counts.values()); p = counts.get("PLAUSIBLE", 0)
    print(f"\nplausible: {p}/{n} = {100*p/max(n,1):.1f}%")
    print(f"results -> {out}")


if __name__ == "__main__":
    main()
