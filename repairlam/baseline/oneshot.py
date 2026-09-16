"""Phase 1 baseline: one prompt, whole file, no tools, no retries."""
import os, sys, time, json, argparse, requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from repairlam.events import EventLog
from repairlam.env import d4j

BASE_URL = os.getenv("BASE_URL", "http://localhost:8603/v1")
MODEL = os.getenv("MODEL", "qwen7b")
BTP = os.path.expanduser("~/btp")
WORK = f"{BTP}/repairlam/workspaces"
LOGS = f"{BTP}/repairlam/logs"
RESULTS = f"{BTP}/repairlam/results"

PROMPT = """You are fixing a bug in a Java file.

The following test is failing:
{failing}

Test output:
{output}

Here is the buggy file:
```java
{code}
```

Return the COMPLETE corrected Java file. Output only the code inside a single
```java block. No explanation."""


def server_ctx():
    import requests
    return int(requests.get(f"{BASE_URL}/models", timeout=30).json()["data"][0]["max_model_len"])


def call_llm(prompt, max_tokens=2048):
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/chat/completions", timeout=600, json={
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    })
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")
    d = r.json()
    return (d["choices"][0]["message"]["content"],
            d["usage"]["prompt_tokens"],
            d["usage"]["completion_tokens"],
            int((time.time() - t0) * 1000))


def extract_code(text):
    if "```java" in text:
        return text.split("```java", 1)[1].split("```", 1)[0].strip()
    if "```" in text:
        return text.split("```", 1)[1].split("```", 1)[0].strip()
    return text.strip()


def run_bug(project, bug, results):
    bug_id = f"{project}-{bug}"
    run_id = f"{bug_id}_{MODEL}_oneshot_{time.strftime('%Y%m%dT%H%M')}"
    log = EventLog(run_id, LOGS)
    wd = f"{WORK}/{bug_id}"
    print(f"\n=== {bug_id} ===", flush=True)

    try:
        if not d4j.checkout(project, bug, wd):
            log.summary(bug_id, "ERROR", model=MODEL, note="checkout failed")
            return "ERROR"

        ok, out = d4j.compile_project(wd)
        if not ok:
            log.summary(bug_id, "ERROR", model=MODEL, note="compile failed")
            return "ERROR"

        tr = d4j.run_tests(wd)
        log.event(bug_id, "BASELINE", tool="run_tests",
                  result_status="fail" if not tr.passed else "pass",
                  result_summary=f"{len(tr.failing)} failing")
        if tr.passed:
            log.summary(bug_id, "ERROR", model=MODEL, note="no failing test")
            return "ERROR"
        print(f"  failing: {tr.failing[:2]}", flush=True)

        path = d4j.buggy_file(wd)
        if not path.exists():
            log.summary(bug_id, "ERROR", model=MODEL, note=f"no file {path}")
            return "ERROR"
        code = path.read_text()
        print(f"  file: {path.name} ({len(code)} chars)", flush=True)

        # Whole-file baseline cannot fit large files in a 16k context.
        # This is a real limitation of the approach, not a harness bug.
        if len(code) > 90000:
            log.summary(bug_id, "TOO_LARGE", model=MODEL,
                        note=f"{len(code)} chars exceeds context")
            print("  -> TOO_LARGE (skipped)", flush=True)
            return "TOO_LARGE"

        prompt = PROMPT.format(failing="\n".join(tr.failing[:5]),
                               output=tr.raw[-2000:], code=code)
        ctx = server_ctx()
        need = int(len(prompt) / 2.8) + 1
        budget = ctx - need - 600
        print(f"  ctx={ctx} prompt~{need} budget={budget}", flush=True)
        if budget < need * 0.9:
            log.summary(bug_id, "TOO_LARGE", model=MODEL,
                        note=f"prompt ~{need} tok, {budget} left of {ctx}")
            print("  -> TOO_LARGE", flush=True)
            return "TOO_LARGE"
        text, ti, to, ms = call_llm(prompt, min(budget, int(need*1.4)+500))
        log.event(bug_id, "BASELINE", tool="llm_patch", tokens_in=ti,
                  tokens_out=to, latency_ms=ms, model=MODEL,
                  result_status="ok", result_summary=f"{len(text)} chars")
        print(f"  llm: {ti}in/{to}out {ms}ms", flush=True)

        path.write_text(extract_code(text))

        ok, out = d4j.compile_project(wd)
        if not ok:
            log.event(bug_id, "BASELINE", tool="compile",
                      result_status="fail", result_summary=out[-300:])
            log.summary(bug_id, "FAILED", model=MODEL, note="compile error")
            print("  -> FAILED (compile)", flush=True)
            return "FAILED"

        tr2 = d4j.run_tests(wd)
        outcome = "PLAUSIBLE" if tr2.passed else "FAILED"
        log.event(bug_id, "BASELINE", tool="run_tests",
                  result_status="pass" if tr2.passed else "fail",
                  result_summary=f"{len(tr2.failing)} failing")
        s = log.summary(bug_id, outcome, model=MODEL)
        print(f"  -> {outcome}", flush=True)
        results.append(s)
        return outcome

    except Exception as e:
        log.summary(bug_id, "ERROR", model=MODEL, note=str(e)[:300])
        print(f"  -> ERROR {e}", flush=True)
        return "ERROR"
    finally:
        d4j.cleanup(wd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="Lang")
    ap.add_argument("--n", type=int, default=20)
    a = ap.parse_args()

    Path(RESULTS).mkdir(parents=True, exist_ok=True)
    Path(WORK).mkdir(parents=True, exist_ok=True)

    bugs = d4j.active_bugs(a.project)[:a.n]
    print(f"Running {len(bugs)} bugs from {a.project} with {MODEL}")

    results, counts = [], {}
    for b in bugs:
        o = run_bug(a.project, b, results)
        counts[o] = counts.get(o, 0) + 1

    out = Path(RESULTS) / f"phase1_baseline_{a.project}_{MODEL}.json"
    out.write_text(json.dumps({"counts": counts, "runs": results}, indent=2))

    print("\n" + "=" * 40)
    for k, v in sorted(counts.items()):
        print(f"{k:12s} {v}")
    n = sum(counts.values())
    p = counts.get("PLAUSIBLE", 0)
    print(f"\nplausible rate: {p}/{n} = {100*p/max(n,1):.1f}%")
    print(f"results -> {out}")


if __name__ == "__main__":
    main()
