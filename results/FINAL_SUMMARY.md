# Module 4 (Live GitHub Issues): Summary as of this session

Snapshot as of the corrected re-run — more batches are planned, so this reflects the
current state, not a permanent endpoint. See [`live_github_run_summary.md`](live_github_run_summary.md)
for the per-bug table and [`live_timeout_analysis.md`](live_timeout_analysis.md) for the
infrastructure-bug investigation this summary draws on.

## What Module 4 is

Everything so far has evaluated the FSM repair agent on Defects4J (a fixed, curated
benchmark). Module 4 asks a harder question: does it work on real, currently-open bugs in
real, actively-maintained open-source Java projects, with no defects4j database telling it
which file changed or what the trigger test is?

## Pipeline

`repairlam/github/` — built and validated incrementally across three levels of realism
before running unattended:
1. A local seed repo with a fake GitHub client (no network).
2. A real repo created by the user, real PyGithub calls, a synthetic seeded bug.
3. A real fork of `google/guava` with a real, currently-open, unfixed bug (`guava#3493`).

- `repo_env.py` — git+shell environment backend (clone, build, test, commit, push).
  Credential handling: `GIT_ASKPASS` reads `$GITHUB_TOKEN` from the process environment at
  the moment git needs it; the token is never embedded in a URL or command line. This
  followed a real incident (see git history) where an earlier token-embedded-URL approach
  leaked a credential into a git error message — the askpass approach was the fix and has
  been leak-free since.
- `issue_client.py` — thin PyGithub wrapper: read issues, post comments, open PRs, fork
  repos, enable Issues on forks (disabled by default on GitHub forks).
- `pipeline.py` — end-to-end: clone the issue's repo, run the FSM core
  (`repairlam.agent.loop.run_fsm_core`, the same state machine used on Defects4J) against
  it, and on PLAUSIBLE open a real PR; otherwise post an escalation/timeout report as an
  issue comment.
- `live_bug_pipeline.py` + `bug_specs.py` — the reusable orchestrator built to automate the
  process validated manually on `guava#3493`: fork if needed, seed a regression test built
  from the real issue's own repro text, verify it fails against current (buggy) source, push,
  open an issue with the original text plus a credit note, run the pipeline, log the outcome
  to `results/live_run_log.json` incrementally (resumable — already-logged bugs are skipped,
  and specific keys can be force-rerun after an infra fix).

## Curation approach

Every regression test is built directly from the real issue's own repro/expected-vs-actual
text — never guessed from a title. Candidates were dropped when a maintainer's own reply left
the "correct" fix genuinely disputed (`gson#2816`, `guava#1898`, `guava#6226`), when the bug
was concurrency/timing-dependent (unsafe for a deterministic single-shot test), or when it
depended on Android/JDK-version-specific runtime behavior this cluster can't reliably
reproduce. `square/okhttp`/`retrofit` were skipped after discovering both had been
transferred to an unfamiliar GitHub org since prior knowledge of them.

## Results to date: 26 bugs run (2 batches, across guava, gson, jackson-databind)

**7 PLAUSIBLE (real PRs) / 9 ESCALATED / 6 TIMEOUT / 4 SKIPPED** (not reproducible on
re-verify). Full table: [`live_github_run_summary.md`](live_github_run_summary.md).

The first full run of the second batch scored a misleadingly bad 3 PLAUSIBLE / 7 ESCALATED /
16 TIMEOUT. Investigating the TIMEOUTs found two infrastructure bugs, not model weaknesses:

1. **gson's build requires JDK 17+**; this cluster only had JDK 11, so every gson run failed
   to compile before the FSM ever saw a real test signal (worst case burned its entire turn
   budget calling `get_test_output` in a loop against an unchanging build error). Fixed with
   an isolated JDK 21 conda env scoped to just gson's `test_cmd`. A first attempt at this fix
   upgraded the *shared* `repairlam` env in place and broke Defects4J entirely
   (`repairlam/env/d4j.py` hardcodes `JAVA_HOME` to that same env) — caught via a live
   `defects4j compile` check before it did any real damage, reverted, redone isolated.
2. **`search_repo` was surfacing guava's irrelevant `android/` source mirror** ahead of the
   real source tree, misdirecting the model into editing files the build never compiles.
   One-line sort-key fix in `repairlam/tools/read.py`.

Re-running the 22 affected bugs against the fixed infrastructure changed the picture
substantially: gson's real PLAUSIBLE rate (once it had a working build) is 4/16 attempted
bugs, in the same range as guava's — not the 0/19 the broken build produced. Real PRs went
from 3 to 7.

## Known open items

- 4 gson bugs came back SKIPPED (regression test no longer reproduces the bug). Most likely
  explanation: old issues silently fixed by a later unrelated refactor, never closed — but
  not fully verified against a subtly-wrong test on this session's part.
- `guava#3790` reached the real file on re-run (the `android/`-mirror fix worked) but still
  only reached ESCALATED, not PLAUSIBLE — under active investigation (see the guava#3790
  deep-dive this session is also producing).
- A third curation wave (aiming for 20-30 more bugs, more repos) is in progress as of this
  summary; check `live_run_log.json` and `live_github_run_summary.md` for the latest counts.
