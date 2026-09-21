# Module 4: Live GitHub Issue Runs — Summary

Full outcome log: [`live_run_log.json`](live_run_log.json).

## Process

For each bug: fork the upstream repo (idempotent), write a regression test built
directly from the real issue's own repro/expected-vs-actual text, verify it fails
against the current (buggy) source, push it to the fork, enable Issues on the fork
if needed, open an issue with the original text plus a credit note back to the
source issue, then run the live FSM pipeline
(`repairlam.github.live_bug_pipeline` + `bug_specs.py`) against it. All git network
operations use the `GIT_ASKPASS` credential mechanism
(`repairlam.github.repo_env.git_auth_env`) — no token is ever embedded in a URL.

Curation bar: open, bug/defect-labeled, a clear repro or expected/actual pair in
the issue body (mechanically transcribable into a test, not invented), and no
maintainer dispute over what the "correct" fix even is. Concurrency/timing bugs,
Android- or JDK-version-specific runtime quirks, and issues where a maintainer's
own reply left the fix direction genuinely unsettled were excluded as unfair to
score PLAUSIBLE/ESCALATED/TIMEOUT — e.g. `gson#2816`, `guava#1898`, `guava#6226`
were investigated and dropped for this reason.

Candidate pool: ~193 open bug/defect-labeled issues surveyed across
google/guava, google/gson, FasterXML/jackson-databind, netty/netty,
mockito/mockito, google/truth, and square/moshi. `square/okhttp` and
`square/retrofit` were skipped after their GitHub API responses revealed both
repos had been transferred to an unfamiliar org (`lysine-dev`) since prior
knowledge of them. netty/mockito/moshi/truth ultimately contributed no
candidates that cleared the bar (mostly concurrency-adjacent, Gradle-based
untested infra, or too thin a labeled-issue pool) or were dropped for
maintainer disagreement. Landed on **26 total bugs run** (across guava,
gson, and jackson-databind) rather than the initially-targeted 30-40 — the
quality bar was kept even after the throughput-oriented curation pass.

## Results

**PLAUSIBLE: 3 | ESCALATED: 7 | TIMEOUT: 16** (26 total)

| Bug | Outcome | Turns | Edits | Link |
|---|---|---|---|---|
| guava#3493 | PLAUSIBLE | 27 | 4 | [PR #2](https://github.com/JeetM2207/guava/pull/2) |
| guava#5284 | PLAUSIBLE | 32 | 2 | [PR #4](https://github.com/JeetM2207/guava/pull/4) |
| guava#1065 | PLAUSIBLE | 15 | 1 | [PR #6](https://github.com/JeetM2207/guava/pull/6) |
| jackson-databind#3067 | ESCALATED | 33 | 0 | [comment](https://github.com/JeetM2207/jackson-databind/issues/1) |
| gson#2190 | ESCALATED | 32 | 2 | [comment](https://github.com/JeetM2207/gson/issues/3) |
| gson#1735 | ESCALATED | 28 | 0 | [comment](https://github.com/JeetM2207/gson/issues/6) |
| gson#630 | ESCALATED | 29 | 2 | [comment](https://github.com/JeetM2207/gson/issues/9) |
| gson#523 | ESCALATED | 32 | 2 | [comment](https://github.com/JeetM2207/gson/issues/11) |
| gson#2817 | ESCALATED | 24 | 6 | [comment](https://github.com/JeetM2207/gson/issues/13) |
| gson#1397 | ESCALATED | 27 | 0 | [comment](https://github.com/JeetM2207/gson/issues/19) |
| gson#2680 | TIMEOUT | 30 | 0 | [comment](https://github.com/JeetM2207/gson/issues/1) |
| guava#3790 | TIMEOUT | 38 | 2 | [comment](https://github.com/JeetM2207/guava/issues/7) |
| guava#3768 | TIMEOUT | 38 | 3 | [comment](https://github.com/JeetM2207/guava/issues/8) |
| gson#2348 | TIMEOUT | 36 | 2 | [comment](https://github.com/JeetM2207/gson/issues/2) |
| gson#1994 | TIMEOUT | 34 | 0 | [comment](https://github.com/JeetM2207/gson/issues/4) |
| gson#1736 | TIMEOUT | 30 | 0 | [comment](https://github.com/JeetM2207/gson/issues/5) |
| gson#1511 | TIMEOUT | 32 | 1 | [comment](https://github.com/JeetM2207/gson/issues/7) |
| gson#1394 | TIMEOUT | 30 | 0 | [comment](https://github.com/JeetM2207/gson/issues/8) |
| gson#600 | TIMEOUT | 31 | 1 | [comment](https://github.com/JeetM2207/gson/issues/10) |
| gson#2638 | TIMEOUT | 30 | 0 | [comment](https://github.com/JeetM2207/gson/issues/12) |
| gson#1920 | TIMEOUT | 31 | 0 | [comment](https://github.com/JeetM2207/gson/issues/14) |
| gson#1727 | TIMEOUT | 37 | 1 | [comment](https://github.com/JeetM2207/gson/issues/15) |
| gson#2769 | TIMEOUT | 30 | 0 | [comment](https://github.com/JeetM2207/gson/issues/16) |
| gson#453 | TIMEOUT | 37 | 2 | [comment](https://github.com/JeetM2207/gson/issues/17) |
| gson#1575 | TIMEOUT | 31 | 1 | [comment](https://github.com/JeetM2207/gson/issues/18) |
| gson#996 | TIMEOUT | 30 | 0 | [comment](https://github.com/JeetM2207/gson/issues/20) |

## Open question

All 3 PLAUSIBLE outcomes (and the only real PRs) are on guava; gson went 0/19 for
PLAUSIBLE, with most gson bugs hitting the 30-turn cap without ever landing an
edit that passed. Not yet root-caused — worth checking the per-turn traces in
`repairlam/logs/` for whether the gson reactor build/test loop is simply slower
per iteration (eating turns on `run_tests` calls) versus a genuine model
weakness on gson's codebase/conventions, before drawing conclusions.
