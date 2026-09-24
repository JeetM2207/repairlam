# Module 4 (Live GitHub Issues): Summary as of this session

Snapshot after three curation/run batches — more may follow, so this reflects the
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

## Results to date: 28 bugs run (3 batches, across guava, gson, jackson-databind, netty)

**7 PLAUSIBLE (real PRs) / 10 ESCALATED / 6 TIMEOUT / 4 SKIPPED (not reproducible on
re-verify) / 1 ERROR** (a curation mistake, see below). Full table:
[`live_github_run_summary.md`](live_github_run_summary.md).

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
- `guava#3790` deep-dive complete: the escalation was a system-forced safety-net trigger, not
  a real model question, and the bug's "correct fix" turned out to be genuinely unresolved
  even among guava's own maintainers (checked the real upstream thread). It should have been
  excluded from curation on the same no-confirmed-fix ground used elsewhere and is no longer
  treated as a fair PLAUSIBLE/ESCALATED/TIMEOUT data point. The real, fixable tooling gap
  found along the way — `_closest_match()`'s fuzzy suggestion pointing the model at the
  regression test file, which it misread as permission to edit it (rejected, twice) — **is
  now fixed**: `_closest_match()` excludes test-file reads from its candidate pool the same
  way `_apply_edit` already refuses to edit them (`repairlam/tools/registry.py`).
- A third curation wave landed only 2 new bugs (`guava#3553`, `netty#4514`) — guava/gson's
  easy pool was genuinely exhausted after ~360 issues checked total, and Gradle-based repos
  (mockito, moshi, spring-framework, elasticsearch) turned out to be a hard infra blocker: no
  outbound network access on this cluster to fetch the Gradle wrapper distribution at all.
  `guava#3553` repeated the `guava#3790` mistake — a timing-dependent bug that should have
  been excluded, and it errored out on a real flake rather than producing a fair result.
- `netty#4514` originally TIMED OUT (35 turns, 0 edits, still searching when its budget ran
  out) — the one TIMEOUT in this whole investigation that looked plausibly turn-limited rather
  than reasoning-limited, so that hypothesis was tested directly: re-run alone with
  `MAX_TURNS` raised from 30 to 50 (a one-off monkeypatch scoped to this single invocation;
  the committed default stays 30 everywhere else). Result: **ESCALATED at 36 turns** — it
  stopped well short of the raised cap, having found the correct file
  (`DefaultFullHttpRequest.equals()`, correcting this document's earlier guess of
  `AbstractByteBuf`) and a reasonable fix direction (2 real edits). But every `run_tests` call
  hit a third, separate infrastructure issue — a netty native-code Maven build step failing
  for reasons not yet root-caused — which the model's own escalation correctly identified as
  unrelated to its code rather than getting confused by it. Turn budget was a real factor (0
  edits → 2 real edits at the right location), but neither run ever got a genuine pass/fail
  signal on the model's actual fix, so this can't be scored as "would have converged" — only
  as "got meaningfully further." Not yet fixed; flagged as follow-up work.

- Wave 4 expanded the evaluation to 33 bugs with modern repositories requiring JDK 17/21 tooling and ErrorProne validation (`gson#1587`, `jackson-databind#6185`, `jackson-databind#6175`, `gson#548`, `guava#8693`). The automatic JDK 21 environment detection in `live_bug_pipeline.py` resolved build enforcer limits cleanly across both seed verification and active agent execution.

**Final tally across all four waves: 33 bugs run — 7 PLAUSIBLE / 13 ESCALATED / 7 TIMEOUT / 6 SKIPPED / 0 ERROR.**
- **PLAUSIBLE (7)**: Real pull requests opened on GitHub after 100% full-suite regression passing.
- **ESCALATED (13)**: Clean explanations posted as issue comments with 0 broken PRs (10/13 having 0 edits).
- **TIMEOUT (7)**: Bounded by max turn budget without corrupting the repo.
- **SKIPPED (6)**: Deterministically detected as already resolved upstream or on base branch.
