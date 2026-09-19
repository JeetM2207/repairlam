# RepairLAM — Progress Summary

**Setup:** FSM repair agent (UNDERSTAND → COLLECT → TRY_FIX → REFLECT),
Qwen2.5-Coder-32B-Instruct-GPTQ-Int4, evaluated on Defects4J Apache Commons
Lang. Baseline (one-shot, no tools) scores 0/20 plausible on the same bugs.

## What the agent achieves

The FSM loop reliably drives the model through the intended repair
protocol — localize via a test failure, read source, propose an anchored
edit, run tests, reflect and retry — without crashes, runaway processes,
or unrecoverable parsing failures, across four full-scale unattended runs
(2×n=30, 2×n=10, ~100 bug-attempts total) run overnight with no manual
intervention. Compile/checkout errors: 0. Uncaught exceptions: 0. Every
JSON parse failure self-healed via the existing repair fallback, including
several 3-5-in-a-row cascades at `temperature=0.0`. The agent consistently
lands real, compiling, test-running edits — the question this session
answered is *why* none of them fix the actual bug.

## Three failure modes found and fixed

Each fix was isolated, unit-verified, then confirmed on a live run before
being scaled up — never committed on the strength of the idea alone.

| # | Failure mode | Fix | Before → After |
|---|---|---|---|
| 1 | Model burns its entire read budget re-reading one file (usually the test file), never reads the source file, then hallucinates an `apply_edit` anchor from training memory once reads are blocked. | Track reads per file path per bug; on a repeat read of the same path, inject a system message directing the model to the source file instead. | Zero-edit escalations: **17/30 (57%) → 3/10 (30%)**. Bugs landing ≥1 real edit: 13/30 → 7/10. |
| 2 | `apply_edit` rejected as **ambiguous** (anchor matches multiple places in repetitive code); model blindly retried the identical snippet. | Rejection message now explicitly tells the model not to retry the same snippet and to expand context (enclosing method signature, surrounding lines). | Of 54 `apply_edit` calls on the verification run: 9 ambiguous, 4/9 (44%) recovered to a successful edit within 2 retries — versus the old behavior of repeating the same rejected snippet indefinitely. |
| 3 | `apply_edit` rejected as **not_found** — anchor text invented from training data, not present anywhere in the file. This was the *dominant* rejection reason (29/54, 53.7% of all `apply_edit` calls). | Every `read_file` call's literal output is now recorded per bug. On a `not_found` rejection, fuzzy-match (`difflib.get_close_matches`) the rejected text against everything read this run and show the model the closest real snippet, with its actual file and line number. | `not_found` rate: **53.7% → 24.7%** of all `apply_edit` calls (3-bug sanity check: 10%; full n=30 confirmation: 47/190). Every suggestion verified to be real code at a real location, not fabricated. |

## Final result: 0/30 plausible

Despite all three fixes measurably improving their targeted metric — more
edits landing, fewer wasted attempts, fewer hallucinated anchors — the
plausible count did not move off zero across any of the four full-scale
runs this session (original n=30, two n=10 verification runs, final n=30
with all fixes active: 18 ESCALATED / 12 TIMEOUT / **0 PLAUSIBLE**). The
agent got measurably better at the mechanics of proposing an edit and
measurably no better at proposing the *correct* one.

## Root cause: method-level localization, not tooling

A direct comparison of the model's actual edits against the real
developer patches (Defects4J `patches/<id>.src.patch`) for three bugs with
clean, real edit attempts (`results/edit_quality_analysis.md`) found:

- **File-level localization works.** All edits across all three bugs
  landed in the developer's actual modified file — the oracle hint
  (`buggy_file()`) is doing its job.
- **Method-level localization fails.** Two of three bugs never found the
  defective method at all and instead edited or fabricated an unrelated,
  plausible-looking method in the same file. The third found the right
  method but the wrong branch, and partly reversed its own edit across two
  attempts.
- **Deletion bias.** All three real fixes were partial or full deletions
  of buggy code (a leading-zero-stripping loop, an entire mishandled
  branch, a hardcoded capacity formula). Every model edit was an addition
  or a small conditional tweak — never a deletion. The anchored,
  one-`find`→`replace`-at-a-time edit tool may itself be structurally
  biasing the model away from proposing the large removals these bugs
  actually need.

This is not a tooling, parsing, or anchor-matching problem — by the time
these edits landed, `apply_edit` had already confirmed the anchor text was
real and unique. The gap is upstream: fault localization within a file,
and a bias toward additive edits over the deletions several of these bugs
require.
