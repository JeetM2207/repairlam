# Live GitHub Track: TIMEOUT Root-Cause Analysis

Companion to the Defects4J-track [`timeout_lastedit_analysis.md`](timeout_lastedit_analysis.md),
but for the live-GitHub-issue results in [`live_github_run_summary.md`](live_github_run_summary.md).
The original overnight batch produced 3 PLAUSIBLE / 7 ESCALATED / 16 TIMEOUT across 26 bugs.
Investigating those 16 TIMEOUTs surfaced two distinct, previously-unknown infrastructure bugs —
neither is a model-reasoning limitation — that made nearly all of them uninformative as "model
ran out of turns" data points. Both are now fixed, and every affected bug was re-run.

## Root cause 1: gson's build requires a JDK this cluster didn't have

gson's parent pom enforces `DeserializationFeature`-unrelated build tooling via
`maven-enforcer-plugin`'s `RequireJavaVersion` rule, which demands JDK 17-26. The `repairlam`
conda env (which `repairlam.env.d4j` also hardcodes `JAVA_HOME` to, for the Defects4J track)
only had JDK 11.0.30, and no JDK 17+ existed anywhere on the machine.

Every one of the 20 gson runs in the original batch hit this enforcer failure starting at
turn 1 — the FSM never once got a real test-failure signal for any gson bug. The worst case
(`gson#1394`) burned its entire ~30-turn budget calling `get_test_output` in a loop, never
even reaching COLLECT, because the build output never changed. This also silently fooled the
orchestrator's own "confirm bug present" check (`live_bug_pipeline._seed_and_verify`, which
just checks the test command's exit code): it read "build never compiles" as "test correctly
fails," so every gson bug was logged as confirmed-buggy for the wrong reason.

**Fix:**
- Installed a second, fully isolated JDK 21 (`conda create -n jdk21tools -c conda-forge
  openjdk=21`) rather than upgrading the shared `repairlam` env in place — the first attempt
  at this did upgrade `repairlam` in place and **broke Defects4J entirely**
  (`defects4j compile` refused to run at all: `Java 11 is required!`). Reverted immediately
  and verified with a real `defects4j checkout`/`compile` on Lang-1b before proceeding.
- gson's `test_cmd` in `bug_specs.py` now runs via `env JAVA_HOME=<jdk21tools> PATH=<jdk21tools>/bin:...`
  wrapping an absolute path to `mvn`, scoped to that one subprocess only — the ambient
  environment (and anything Defects4J touches) is untouched.
- `env` was used instead of `bash -lc`: a login shell re-runs profile scripts and resets
  `PATH`, which silently dropped `mvn` from the override on the first attempt.
- Getting past the enforcer surfaced real compile errors and Error-Prone lint failures
  (`-Werror`) in the regression tests themselves — a wrong package for `Strictness`, a missing
  `throws ParseException`, `IdentifierName`, `AssertThrowsMinimizer`, `UnusedVariable`,
  `YodaCondition`, `HidingField`, `UnnecessarilyFullyQualified`, and `CheckReturnValue`
  violations across several files, previously masked entirely by the enforcer short-circuit.
  All fixed; the full gson test tree now compiles clean under JDK 21 (confirmed via a `mvn
  -pl gson -am test-compile` from a clean `target/`, no cached-compile false negatives).

## Root cause 2: guava's `android/` source mirror misleads `search_repo`

guava's repo contains a full duplicate source tree under `android/` (for the Android-compatible
build flavor). It is **not** part of the Maven reactor `-pl guava-tests -am` builds
(`google/guava`'s root pom `<modules>` list is `guava, guava-bom, guava-gwt, guava-testlib,
guava-tests` — no `android`), so any edit under `android/` is completely inert to the actual
test run.

`repairlam/tools/read.py`'s `search_repo` sorts candidate files by
`("/test/" in path, path)` — this deprioritizes test files (the fix for a previously-known
bug) but has no notion of `android/`, and since `"android" < "guava"` lexicographically, the
irrelevant mirror sorts first for any class name that exists in both trees. Both `guava#3790`
and `guava#3768` got misdirected:

- **`guava#3768`**: spent turns 3-25 reading/editing `android/guava-testlib/...` and
  `android/guava/src/.../ObjectArrays.java` before self-correcting at turn 28 to the real
  `guava/src/.../ObjectArrays.java`. Once there, though, its edits (turns 32, 38) reinforced
  the bug's actual root cause — deriving the result array's type from `array.getClass()`
  (`(Class<? extends T[]>) array.getClass()`, then `(Class<T[]>) array.getClass()`) — instead
  of fixing it (returning a plain `Object[]`, as the correct sibling overload does). This one
  is a genuine model-reasoning gap, not just a tooling artifact.
- **`guava#3790`**: never reached the real file at all in the original run — 100% of its
  edits targeted the inert `android/` copies of `Iterables.java` and `Lists.java`. Its last
  attempted edit (rejected only for an anchor mismatch, still in the wrong file) was a
  reasonable idea: skip empty sublists when building the partition view.

**Fix:** one-line addition to the sort key in `repairlam/tools/read.py:39`:
`("/android/" in path, "/test/" in path, path)` — real source ranks first, then real test
files, then the `android/` mirror (source, then test).

## Re-run

All 20 gson bugs and both guava bugs (`guava#3790`, `guava#3768`) were re-run against the
fixed `search_repo` and the JDK-21-isolated gson build. `results/live_run_log.json` reflects
the corrected outcomes (prior entries for these keys were overwritten, not duplicated).

**Before → after, for the 22 re-run bugs:** 0 PLAUSIBLE / 7 ESCALATED / 15 TIMEOUT →
**4 PLAUSIBLE / 9 ESCALATED / 5 TIMEOUT / 4 SKIPPED**.

Full corrected result set (26 bugs total, including the 4 bugs that were never affected and
didn't need re-running): **7 PLAUSIBLE / 9 ESCALATED / 6 TIMEOUT / 4 SKIPPED** — see
[`live_github_run_summary.md`](live_github_run_summary.md) for the per-bug table and links.
Real PRs went from 3 (all guava) to 7 (3 guava + 4 new gson: `#1511`, `#630`, `#600`,
`#1920`). gson's true PLAUSIBLE rate, once it had a working build, is 4/16 actually-attempted
bugs (excluding 4 SKIPPED as not reproducible) — in the same range as guava's, not the 0/19
the broken build produced.

4 bugs (`gson#1735`, `gson#1394`, `gson#523`, `gson#453`) came back SKIPPED: their
regression test now passes against the fork's current source, meaning the underlying bug is
no longer reproducible. Plausible explanation for at least some of these: they're old issues
(one filed in 2013) that a later, unrelated refactor silently fixed without anyone closing the
tracking issue — a real and common occurrence, not something this pipeline can distinguish
from a subtly-wrong regression test without deeper per-bug investigation. Flagged here as an
open uncertainty rather than asserted as fact.

## Deep dive: `guava#3790` re-run (corrected earlier claim below)

The earlier claim that `guava#3790` "looked winnable" once the `android/` bug was fixed was a
prediction based on its last (inert) edit attempt looking reasonable, not a guarantee, and it
turned out to be substantially wrong once actually checked. Re-run result: ESCALATED, 0 edits
applied, 26 turns, `wall_clock_s: 279.1`.

**The escalation comment is not a real question.** It's the FSM's own safety-net firing after
the model exhausted its read/attempt budget in TRY_FIX without ever landing a single accepted
edit — `run_fsm_core` force-escalates in this situation independently of the model's own
`escalate` tool call (which stays gated behind 2 real fix attempts). The full comment posted
to [the issue](https://github.com/JeetM2207/guava/issues/9) is the generic template:

> 🤖 repairlam attempted this issue and escalated.
>
> Edits attempted: 0
>
> **Reason:**
> read limit exceeded without any edit attempt
>
> _No pull request was opened. This comment was posted automatically; a human should take it
> from here._

**What actually happened, turn by turn:** the `search_repo`/`android/` fix worked — this run
correctly landed on the real `guava/src/com/google/common/collect/Lists.java` (unlike the
original run, which never left the `android/` mirror). But every one of its 4 `apply_edit`
attempts was rejected:

- Turns 16 and 26 both guessed `find` text that was never actually read in this
  conversation — `if (current.isEmpty()) {` and `if (subList.isEmpty()) {\n listIterator.remove();\n}`
  — plausible-sounding guava-style code, but not present anywhere in the 1219-line file. This
  is the same hallucinated-anchor failure mode noted as "recently fixed" in `CLAUDE.md`,
  recurring here: it read lines 100-250 of `Lists.java` and never located the actual
  `Partition`/iterator code (which is much further down the file), then guessed instead of
  reading further.
- Turns 19 and 25, after each hallucination failure, misread the tool's own
  `_closest_match()` "closest real text found in ... PartitionRemoveAll3790Test.java" fuzzy
  suggestion as permission to edit the *test* file, and tried to — twice, both correctly
  rejected ("editing test files is not allowed"). This is a real, fixable tooling gap:
  `_closest_match()` should exclude test-file matches when the target path is a source file,
  the same way `search_repo`'s ranking already deprioritizes tests — right now it's actively
  misleading the model into a rule violation instead of helping it find the real anchor.

**What the actual correct fix is: genuinely unresolved, even upstream.** Checking the real
`google/guava#3790` comment thread (which should have been checked more carefully during
curation) shows guava's own maintainers never reached consensus. `dimo414` and `netdpb`
diagnose the root cause precisely: `Lists.java`'s `Partition` inner class extends
`AbstractList` but doesn't implement the `modCount`-based comodification tracking that gives
`ArrayList`'s iterator its fail-fast `ConcurrentModificationException` behavior, so a
structural mutation during iteration surfaces as a confusing `NoSuchElementException` instead
of the well-documented, expected `ConcurrentModificationException`. `netdpb`'s suggested
direction — make `hasNext()` call `checkForComodification()` — is the closest thing to an
informed fix proposal in the thread, but it was never implemented, confirmed, or turned into
a PR; the thread ends in unresolved back-and-forth about what the "expected" behavior even
is. **This bug should have been excluded from curation on the same "no maintainer-confirmed
fix" ground used to drop `gson#2816`/`guava#1898`/`guava#6226`** — that check was applied
inconsistently. Retroactively marking it: not a fair PLAUSIBLE/ESCALATED/TIMEOUT data point.

**Verdict on "small prompt nudge vs. genuine reasoning gap": both, layered, and not winnable
as this bug is currently specified.** Fixing `_closest_match()` to stop suggesting test files
is a cheap, worthwhile win in the same class as the two already-shipped fixes, and would give
the model 2 more real turns instead of 2 wasted rejections. But that alone wouldn't convert
this to PLAUSIBLE: the model never read far enough into `Lists.java` to find the real
`Partition` class, its hypothesized direction ("skip empty sublists") doesn't match the one
informed technical lead anyone (including guava's own maintainers) has proposed
(`checkForComodification()`/CME semantics), and the bug's correct resolution was never
actually settled upstream. Recommend dropping `guava#3790` from future scoring rather than
re-attempting it.

## Two other bugs introduced along the way, both caught and fixed before the re-run

- Installing JDK 21 into the shared `repairlam` conda env **broke Defects4J entirely**
  (`defects4j compile` → `Java 11 is required!`) because `repairlam/env/d4j.py` hardcodes
  `JAVA_HOME` to that same env. Caught immediately by testing a Lang-1b checkout/compile,
  reverted to JDK 11.0.30, and JDK 21 was reinstalled in a fully separate `jdk21tools` conda
  env instead — gson's `test_cmd` now overrides `JAVA_HOME`/`PATH` for that one subprocess
  only, via `env` (not a login shell, which resets `PATH` from profile scripts and silently
  dropped `mvn` on the first attempt).
- Getting past gson's enforcer plugin surfaced real compile errors and `-Werror`-enforced
  Error Prone lint failures in the regression tests themselves, previously masked entirely by
  the enforcer short-circuit: a wrong package for `Strictness`, a missing
  `throws ParseException`, and `IdentifierName`/`AssertThrowsMinimizer`/`UnusedVariable`/
  `YodaCondition`/`HidingField`/`UnnecessarilyFullyQualified`/`CheckReturnValue` violations
  across several files. All fixed; verified with a clean (`rm -rf target`) full
  `mvn -pl gson -am test-compile` before launching the re-run.
