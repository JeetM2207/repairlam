# RepairLAM Project

B.Tech thesis: autonomous program repair agent using Large Action Models,
evaluated on Defects4J (Apache Commons Lang).

## Architecture
- repairlam/agent/loop.py — FSM controller (UNDERSTAND -> COLLECT -> TRY_FIX -> REFLECT)
- repairlam/agent/prompts.py — system + state prompts sent to the LLM
- repairlam/tools/registry.py — Dispatcher: routes model tool calls (read_file, apply_edit, run_tests, etc)
- repairlam/tools/edit.py — apply_edit with strict anchor-matching (find must match exactly once)
- repairlam/env/d4j.py — Defects4J CLI wrappers (checkout, compile, run_tests)
- repairlam/events.py — JSONL structured logging, one line per turn

## Model serving
- Qwen2.5-Coder-32B-Instruct-GPTQ-Int4 served via vLLM on port 8603
- Server started with: $BTP/serve32.sh <GPU_ID>
- Check free GPU first with the `gpus` alias before claiming one
- Hardware is Tesla V100 (Volta, compute 7.0): no bf16, no FlashAttention-2,
  vLLM must always use --dtype half --enforce-eager

## Running experiments
- Baseline (one-shot, no tools): python -m repairlam.baseline.oneshot --project Lang --n <N>
- FSM agent: python -m repairlam.agent.loop --project Lang --n <N>
- Single bug: add --only <bug_number> instead of --n
- Logs land in repairlam/logs/*.jsonl (one file per bug run, one JSON line per turn)
- Results summary in repairlam/results/phase2_fsm_Lang_qwen32b.json

## Known constraints
- Shared GPU cluster, no scheduler — always check `gpus` before claiming one
- run_tests targets only the trigger test class during the loop (fast, ~seconds),
  full unfiltered suite only runs at final verification (loop.py, two call sites
  near the end of run_bug, search for "d4j.run_tests(wd)" with no test_class arg)
- MAX_TURNS = 30, read-limit kicks in after 3 reads without an edit
- After any successful apply_edit, the only allowed next action is run_tests
  (forced via the "allowed" set logic — do not let this regress)
- Escalation is blocked until at least 2 real fix attempts have been made

## Recently fixed bugs (do not reintroduce)
1. search_repo used to rank test files before source files — fixed by
   sorting `/test/` paths last
2. apply_edit was receiving line-number prefixes ("   42| ") from read_file
   output pasted into find/replace — now stripped automatically, and the
   prompt explicitly warns against including them
3. Model was hallucinating anchor text that didn't exist in the file at all
   (invented code from training data) — prompt now says find must be copied
   verbatim from the most recent read_file call, never written from memory
4. Orphaned java/ant child processes from interrupted runs would survive
   subprocess timeouts and silently steal CPU on future runs — fixed by
   using subprocess.Popen with start_new_session=True and os.killpg on
   timeout in repairlam/env/d4j.py's _run()
5. Model's JSON output sometimes contains raw unescaped newlines inside
   string values, breaking json.loads with "Expecting ',' delimiter" —
   fixed with a _repair_json() fallback in parse_action() that escapes
   literal newlines/tabs inside string boundaries before reparsing

## Current goal
Get a clean run of --project Lang --n 20 with zero parse_error entries,
then compare plausible/escalated/timeout counts against the baseline
(oneshot.py), which scores 0/20 plausible on the same 20 bugs.
