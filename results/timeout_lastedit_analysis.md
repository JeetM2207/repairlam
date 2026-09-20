# Were TIMEOUT bugs close to the fix, or wrong direction entirely?

Source run: `results/phase2_run30_searchfix_final.json` (n=30 Lang, search_repo
fixes active). 19 of 30 bugs ended TIMEOUT. For each, this looks at the
model's actual **last `apply_edit` attempt** before the turn budget ran out,
and asks two questions: (1) was it in the same method as the real fix, and
(2) if so, was it actually *converging* on that fix, or just doing something
else nearby.

**Methodology.** File-location checks alone are unreliable here: by the time
of a bug's last edit, 3-8 earlier edits in that same run had already changed
the file, so comparing the last edit's anchor text against the pristine
buggy checkout gives false negatives. Each bug's edit sequence was **replayed
in order** against a fresh copy of the buggy checkout (using the project's
own `apply_edit`), reproducing the true file state at the moment of the final
edit, then checked whether that edit's anchor falls inside the ground-truth
method's body (`repairlam/analysis/ground_truth.py`). For the same-method
cases, the real fix was pulled directly from fresh `defects4j checkout -v
<id>b` / `-v <id>f` pairs (not the `.src.patch` files, to avoid the direction
error found and corrected earlier this session) and compared by hand against
what the model actually wrote.

## Headline

| | count |
|---|---|
| Wrong direction entirely (different method) | 12/19 |
| Same method as the real fix | 7/19 |
| — of which genuinely close (same line/logic, one turn from correct) | 1 (Lang-27) |
| — of which borderline (same *class* of tiny bug, wrong line) | 1 (Lang-6) |
| — of which same method but last edit was self-correcting its own earlier mistake | 5 (Lang-1, 4, 20, 24, 30) |

**So: strictly "close," 1-2 of 19. Not meaningfully progressing even though
in the right method, 5 of 19. Wrong direction entirely, 12 of 19.**

## Wrong direction entirely (12/19)

Lang-8, 9, 11, 12, 13, 17, 26, 28, 29, 31, 32, 33 — last edit landed in a
different method (sometimes a different *file*, e.g. Lang-26's last edit was
in `maven-build.xml`, not the Java source at all) than the real fix. Right
file/project area in most cases (matches the run's overall 60% file-level
localization), but the specific method the last edit targeted was not where
the bug lives.

## Same method, but not close (5/19)

In every one of these, the last edit is the model **cleaning up a syntax
error or duplicate token it introduced itself** in an earlier turn, not
making progress toward the real bug.

| Bug | Last edit (find → replace) | Real fix | Read |
|---|---|---|---|
| Lang-1 | `numDecimals = s` → `numDecimals = str.length() - decPos - 1;` | Adds a leading-zero-stripping loop + refines the hex overflow check | Fixing a garbled anchor from its own earlier edit; nowhere near the hex-parsing bug |
| Lang-4 | `return -1;` → `return 0;` | Changes `HashMap<CharSequence,...>` to `HashMap<String,...>` (key-equality bug) + adds `.toString()` at lookup sites | Guessed a return-value tweak; the real bug is a type/hashing issue with no return-value change at all |
| Lang-20 | `for (...endIndex; endIndex; i++)` → `for (...endIndex; i++)` | Simplifies the `StringBuilder` capacity formula | Removing a duplicate token it introduced itself; unrelated to the capacity bug |
| Lang-24 | duplicate `if` condition → single condition | `return foundDigit && !hasExp;` → adds `&& !hasDecPoint` | Removing its own redundant condition; the real fix *adds* a condition elsewhere |
| Lang-30 (rejected) | `searchChars[j] == ch` → `searchChars[j] == (char) ch` | Adds high-surrogate pairing logic around the match | A type-cast guess that doesn't touch surrogate handling; never even applied |

## Genuinely close (1-2/19)

**Lang-27 — the closest call in the whole set.** Real fix:

```diff
 if (expPos > -1) {
-    if (expPos < decPos) {
+    if (expPos < decPos || expPos > str.length()) {
         throw new NumberFormatException(str + " is not a valid number.");
     }
```

Model's last edit: `if (expPos < decPos && expPos > 0)` → `if (expPos < decPos)`.
Same exact conditional. The model had earlier added a wrong extra clause
(`&& expPos > 0`) and its last action removes it again — landing back on the
*original buggy* condition, one clause short of correct. This is the one case
in the run that looks like genuine, if unfinished, convergence: right line,
right idea (the condition needs an extra clause), wrong specific clause.

**Lang-6 — borderline.** Real fix is a one-character variable typo:
`Character.codePointAt(input, pos)` should be `codePointAt(input, pt)`. The
model's last edit fixes a *different* one-character-class issue (`pos+= `→
`pos += `, a spacing typo on a different line in the same loop). Same method,
same "tiny loop-variable bug" shape, wrong specific line — closer in kind
than in fact.

## Synthesis

Reaching the right method is necessary but nowhere near sufficient. Even
among the 7/19 bugs that got there, 5 spent their last turn defensively
patching a mistake they'd made themselves rather than advancing toward the
real fix -- the read-limit and turn-budget pressure that successfully forces
commitment during COLLECT doesn't prevent this kind of unproductive churn
once inside TRY_FIX/REFLECT. Only Lang-27 shows what real, incremental
progress toward a correct fix looks like from this model at temperature 0.
