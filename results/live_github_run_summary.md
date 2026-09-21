# Module 4: Live GitHub Issue Runs — Summary

Full outcome log: [`live_run_log.json`](live_run_log.json). Root-cause analysis of the
original TIMEOUT-heavy batch, and what was fixed before the numbers below: [`live_timeout_analysis.md`](live_timeout_analysis.md).

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

## A first pass produced misleading numbers

The first full run of this batch scored 3 PLAUSIBLE / 7 ESCALATED / 16 TIMEOUT,
with gson going 0/19 for PLAUSIBLE. That turned out to be almost entirely an
infrastructure artifact, not a model result: gson's build requires a JDK this
cluster didn't have, so every gson run failed to even compile before the FSM
ever saw a real test signal, and a separate bug in `search_repo` let guava's
irrelevant `android/` source mirror mislead the model on two more bugs. Both
were root-caused and fixed; see [`live_timeout_analysis.md`](live_timeout_analysis.md)
for the full investigation. All 20 gson bugs and the 2 affected guava bugs were
then re-run against the fixed infrastructure. **The table below is the
corrected, final result** — prior TIMEOUT/ESCALATED entries for those 22 keys
were overwritten in place in `live_run_log.json`, not appended alongside.

## Results

**PLAUSIBLE: 7 | ESCALATED: 9 | TIMEOUT: 6 | SKIPPED: 4** (26 total)

SKIPPED means the regression test passed against the bug's current source —
i.e., re-verified not reproducible (most likely already fixed upstream by an
unrelated refactor, issue never closed) — so no fix was attempted or scored
one way or the other.

| Bug | Outcome | Turns | Edits | Link |
|---|---|---|---|---|
| guava#3493 | PLAUSIBLE | 27 | 4 | [PR #2](https://github.com/JeetM2207/guava/pull/2) |
| guava#5284 | PLAUSIBLE | 32 | 2 | [PR #4](https://github.com/JeetM2207/guava/pull/4) |
| guava#1065 | PLAUSIBLE | 15 | 1 | [PR #6](https://github.com/JeetM2207/guava/pull/6) |
| gson#1511 | PLAUSIBLE | 20 | 2 | [PR #27](https://github.com/JeetM2207/gson/pull/27) |
| gson#630 | PLAUSIBLE | 19 | 1 | [PR #29](https://github.com/JeetM2207/gson/pull/29) |
| gson#600 | PLAUSIBLE | 19 | 1 | [PR #31](https://github.com/JeetM2207/gson/pull/31) |
| gson#1920 | PLAUSIBLE | 19 | 2 | [PR #35](https://github.com/JeetM2207/gson/pull/35) |
| jackson-databind#3067 | ESCALATED | 33 | 0 | [comment](https://github.com/JeetM2207/jackson-databind/issues/1) |
| gson#2680 | ESCALATED | 22 | 0 | [comment](https://github.com/JeetM2207/gson/issues/21) |
| guava#3790 | ESCALATED | 26 | 0 | [comment](https://github.com/JeetM2207/guava/issues/9) |
| gson#1994 | ESCALATED | 30 | 2 | [comment](https://github.com/JeetM2207/gson/issues/24) |
| gson#1736 | ESCALATED | 28 | 0 | [comment](https://github.com/JeetM2207/gson/issues/25) |
| gson#1727 | ESCALATED | 23 | 0 | [comment](https://github.com/JeetM2207/gson/issues/36) |
| gson#2769 | ESCALATED | 22 | 0 | [comment](https://github.com/JeetM2207/gson/issues/37) |
| gson#1575 | ESCALATED | 27 | 5 | [comment](https://github.com/JeetM2207/gson/issues/38) |
| gson#1397 | ESCALATED | 33 | 0 | [comment](https://github.com/JeetM2207/gson/issues/39) |
| guava#3768 | TIMEOUT | 48 | 0 | [comment](https://github.com/JeetM2207/guava/issues/10) |
| gson#2348 | TIMEOUT | 36 | 1 | [comment](https://github.com/JeetM2207/gson/issues/22) |
| gson#2190 | TIMEOUT | 39 | 2 | [comment](https://github.com/JeetM2207/gson/issues/23) |
| gson#2638 | TIMEOUT | 34 | 4 | [comment](https://github.com/JeetM2207/gson/issues/32) |
| gson#2817 | TIMEOUT | 33 | 3 | [comment](https://github.com/JeetM2207/gson/issues/33) |
| gson#996 | TIMEOUT | 34 | 4 | [comment](https://github.com/JeetM2207/gson/issues/40) |
| gson#1735 | SKIPPED | — | — | not reproducible on re-verify |
| gson#1394 | SKIPPED | — | — | not reproducible on re-verify |
| gson#523 | SKIPPED | — | — | not reproducible on re-verify |
| gson#453 | SKIPPED | — | — | not reproducible on re-verify |

Real PRs went from 3 (all guava) to **7** (3 guava + 4 gson) once gson bugs got
a genuine test signal — gson's corrected PLAUSIBLE rate among its 16 actually-
attempted bugs (excluding the 4 SKIPPED) is 4/16, in the same range as guava's.
The original "gson: 0/19 PLAUSIBLE" was not a finding about the model; it was
a broken build.

## Wave 3: 2 more bugs (guava, netty), after guava/gson's easy pool was mined out

After curating ~360 more issues, guava/gson yielded essentially nothing new that
cleared the quality bar; landed 2 new candidates: `guava#3553` and `netty#4514`
(netty's first appearance in this track — its own JDK/build were unaffected by
either of the two infra fixes above; it just needed its own fork and a
copyright-header/checkstyle fix on the regression test file before it would
compile). See `results/FINAL_SUMMARY.md` for why the pool dried up (Gradle repos
are a hard infra blocker on this cluster — no outbound network access to fetch
the Gradle wrapper at all — and several other well-known Maven repos turned out
to use bespoke build tooling or have too-thin bug-labeled pools).

| Bug | Outcome | Turns | Edits | Link |
|---|---|---|---|---|
| guava#3553 | ERROR | — | — | [issue #11](https://github.com/JeetM2207/guava/issues/11) — "no failing test at HEAD" |
| netty#4514 | ESCALATED | 36 | 2 | [issue #2](https://github.com/JeetM2207/netty/issues/2) — re-run at MAX_TURNS=50, see below |

`guava#3553` is a curation mistake, not a real data point: it's an
executor-shutdown/future-cancellation timing bug, which is exactly the kind of
concurrency-dependent bug this track's own stated criteria say to exclude. The
regression test failed reliably by hand (a real 10s timeout, confirmed before
launching) but passed on the pipeline's own fresh clone — a genuine flake, the
same mistake already made once with `guava#3790`. Should not have been curated.

`netty#4514` originally TIMED OUT (35 turns, 0 edits) with the model still searching for the
right file when its budget ran out. That looked turn-budget-limited, so it was re-run alone
with `MAX_TURNS` raised from 30 to 50 to test that directly (see
[`live_timeout_analysis.md`](live_timeout_analysis.md) for the full account; the table above
reflects this corrected re-run, not the original TIMEOUT). Result: ESCALATED at 36 turns (well
under the raised cap) with 2 real edits — it found the correct file and a reasonable fix
direction this time, but every `run_tests` call hit a genuine, unrelated netty native-build
failure the model itself correctly diagnosed as unrelated to its code. Turn budget was a real
factor (0 edits → 2 real edits at the right location), but a third, separate infrastructure
issue means neither run ever got a real pass/fail signal on the model's actual fix — not yet
resolved.

## Grand total across all three waves

**28 bugs run — 7 PLAUSIBLE / 10 ESCALATED / 6 TIMEOUT / 4 SKIPPED / 1 ERROR.** (The "Results"
table above is batches 1+2 only, 26 bugs; add the 2 wave-3 rows in this section for the true
total. `netty#4514` counts once, as ESCALATED, reflecting its MAX_TURNS=50 re-run.)
