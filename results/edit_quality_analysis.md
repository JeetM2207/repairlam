# Edit quality analysis: model fix vs. developer fix

> **Correction (2026-09-19):** the original version of this document read
> the defects4j patch files backwards. Direct verification via
> `defects4j checkout -v <id>b` vs `-v <id>f` for bugs 1, 5, and 20 confirms
> Lang's `.src.patch` files are oriented **fixed → buggy**, not
> buggy → fixed as assumed below on first pass. The `-` lines in each diff
> are the code present in the *fixed* version; the `+` lines are the code
> present in the *buggy* version. All three "developer's actual fix"
> sections and the closing synthesis have been rewritten to the verified
> correct direction. The prior version claimed all three real fixes were
> deletions — they were not; two are substantial additions and one is a
> simplification. The model's own edits (extracted directly from its
> `apply_edit` calls) are unaffected by this correction and are unchanged
> below.

Source run: `results/phase2_run30_anchorfix_final.json` (n=30 Lang, all three
anchor fixes active: read-tracking nudge, ambiguous-anchor context request,
not_found fuzzy-match suggestion). Every bug in that run applied edits that
compiled and ran, but none reached PLAUSIBLE. This picks 3 of those bugs and
lines the model's actual edits up against the developer's real fix, pulled
from `~/btp/defects4j/framework/projects/Lang/patches/<id>.src.patch`.

Selection: bugs with a small, clean edit count (2-3 edits) so the comparison
stays legible — Lang-1 (3 edits, TIMEOUT), Lang-5 (3 edits, ESCALATED),
Lang-20 (2 edits, TIMEOUT).

**Headline finding**: in all three cases the model's edits landed in the
*correct file* — every bug is given the developer's actual modified file as
a hint (`d4j.buggy_file()`, printed each turn as "The defect is in: ..."),
and the model always honored that hint at the file level. What it never did
is find the actual defective *method* inside that file. This is a
method-level localization failure, not a file-level one.

---

## Lang-1 — `NumberUtils.java`

**Developer's actual fix** (`patches/1.src.patch`, verified by direct
checkout diff), in `createNumber`'s hex branch, around line 464 — the buggy
version counts hex digits without stripping leading zeroes first, so a
string like `"0x00000000000000001"` gets misjudged as overflowing `int`/
`long` when it doesn't. The fix **adds** a leading-zero-stripping loop and
refines the overflow boundary check:

```diff
         if (pfxLen > 0) { // we have a hex number
+            char firstSigDigit = 0; // strip leading zeroes
+            for(int i = pfxLen; i < str.length(); i++) {
+                firstSigDigit = str.charAt(i);
+                if (firstSigDigit == '0') { // count leading zeroes
+                    pfxLen++;
+                } else {
+                    break;
+                }
+            }
             final int hexDigits = str.length() - pfxLen;
-            if (hexDigits > 16) { // too many for Long
+            if (hexDigits > 16 || (hexDigits == 16 && firstSigDigit > '7')) { // too many for Long
                 return createBigInteger(str);
             }
-            if (hexDigits > 8) { // too many for an int
+            if (hexDigits > 8 || (hexDigits == 8 && firstSigDigit > '7')) { // too many for an int
                 return createLong(str);
             }
```

**Model's 3 edits** (all in the same file, all in `toInt`/`toLong`, nowhere
near `createNumber`):

1. Line 120 — `toInt`:
   ```diff
   -    if(str == null) {
   +    if(str == null || str.isEmpty()) {
   ```
2. Line 169 — inserted a new `toLong(String)` overload and touched `toLong`'s
   null check.
3. Line 173 — `toLong(String, long)`:
   ```diff
   -    if (str == null) {
   +    if (str == null || str.isEmpty()) {
   ```

**Verdict: not close.** The model never located the actual defect. It
pattern-matched "NumberFormatException-adjacent method in NumberUtils" from
the test file and added `isEmpty()` guards to two unrelated methods —
plausible-looking Java, zero relationship to the hex leading-zero bug that
the test actually exercises. It got the right file purely from the hint and
then searched the wrong 50 lines of a 1400-line file for the rest of the
run.

---

## Lang-5 — `LocaleUtils.java`

**Developer's actual fix** (`patches/5.src.patch`, verified by direct
checkout diff), in `toLocale(String)` — the buggy version has **no
handling at all** for underscore-prefixed locale strings (e.g. `"_GB"`,
`"_GB_variant"`); any such input falls through into the lowercase-language
branch and gets rejected or misparsed. The fix **adds** an entire 20-line
special-case branch for `ch0 == '_'`:

```diff
         final char ch0 = str.charAt(0);
+        if (ch0 == '_') {
+            if (len < 3) {
+                throw new IllegalArgumentException(...);
+            }
+            ... (18 more lines of the new '_' branch) ...
+            return new Locale("", str.substring(1, 3), str.substring(4));
+        } else {
             final char ch1 = str.charAt(1);
             ...
             return new Locale(str.substring(0, 2), str.substring(3, 5), str.substring(6));
+        }
```

**Model's 3 edits** (all in `toLocale`, all within ~5 lines of the actual
defective block — this is the closest of the three):

1. Line 119:
   ```diff
   -    return new Locale(str.substring(0, 2), str.substring(3, 5));
   +    return new Locale(str.substring(0, 2), str.substring(3, 5), str.substring(6));
   ```
2. Line 118 — **reverses edit 1** on a sibling branch:
   ```diff
   -    if (len == 5) {
   -        return new Locale(str.substring(0, 2), str.substring(3, 5), str.substring(6));
   -    }
   +    if (len == 5) {
   +        return new Locale(str.substring(0, 2), str.substring(3, 5));
   +    }
   ```
3. Line 114 — find/replace text identical in the logged args (a no-op, or a
   change too small to appear before the log's 200-char truncation; either
   way it did not touch the buggy branch).

**Verdict: same method, wrong branch, self-contradictory.** This is the
model's best attempt of the three — it's editing the exact method the bug
is in, a few lines from where the missing `ch0 == '_'` branch needs to be
added. But it never proposes adding that branch, or any underscore-prefix
handling at all; instead it toggles argument counts on `Locale(...)`
constructor calls back and forth across two edits in the unrelated
lowercase-language branch, net effect close to zero, then makes a change
indistinguishable from a no-op. It's rearranging deck chairs next to the
actual bug rather than building the missing wing.

---

## Lang-20 — `StringUtils.java`

**Developer's actual fix** (`patches/20.src.patch`, verified by direct
checkout diff), in the `join(...)` overloads — the buggy version computes
the `StringBuilder` initial capacity from a convoluted formula derived from
only the *first* array element's length (`(array[startIndex] == null ? 16 :
array[startIndex].toString().length()) + 1`), which both under-allocates
for arrays whose later elements are longer and is needlessly elaborate.
The fix **simplifies** it to a flat per-item estimate:

```diff
-        StringBuilder buf = new StringBuilder((array[startIndex] == null ? 16 : array[startIndex].toString().length()) + 1);
+        StringBuilder buf = new StringBuilder(noOfItems * 16);
```
(and the same pattern in a second overload, buggy side using
`+ separator.length()` instead of `+ 1`)

**Model's 2 edits** — neither touches `join` at all:

1. Line 182 — appended a brand-new method after `isEmpty`:
   ```java
   public static boolean isNotEmpty(CharSequence cs) {
       return !isEmpty(cs);
   }
   ```
2. Line 5608 — appended a brand-new method body to `reverse`:
   ```java
   public static String reverse(String str) {
       if (str == null) {
           return null;
       }
       return new StringBuilder(str).reverse().toString();
   }
   ```

**Verdict: not close.** Neither `isNotEmpty` nor `reverse` exists in the
developer's patch at all — the model invented two plausible-looking but
entirely unrelated utility methods. It never found `join`, so run_tests
kept failing on the same assertion turn after turn while the model kept
adding unrelated code elsewhere in the same (very large, 5000+ line)
`StringUtils.java`.

---

## Synthesis

- **File-level localization works**: all 8 edits across 3 bugs landed in
  the developer's actual modified file. The oracle hint (`buggy_file()`) is
  doing its job.
- **Method-level localization is the real gap**: only Lang-5 ever touched
  the correct method, and even there it edited the wrong branch and partly
  reversed its own change. Lang-1 and Lang-20 never found the defective
  method inside a large file and instead edited/fabricated something
  plausible-sounding nearby.
- **No clean addition/deletion bias.** Corrected for the patch-direction
  error above: two of the three real fixes (Lang-1, Lang-5) are
  substantial *additions* (a leading-zero-stripping loop; a whole missing
  underscore-prefix branch), and one (Lang-20) is a *simplification* of an
  overcomplicated formula into something shorter. The model's own edits
  were consistently additive or small conditional tweaks across all three
  bugs regardless. That happens to match the *shape* of what two of the
  three real fixes needed (addition) — so the model's failure here isn't
  explained by an addition-vs-deletion tendency at all. It's explained
  entirely by location: it never edits the method the real fix is in
  (Lang-1, Lang-20), or edits the right method but the wrong branch
  (Lang-5).
- None of this is a parsing, anchor-matching, or tooling failure — by the
  time these edits landed, `apply_edit` had already verified the `find`
  text was real and unique. The gap is upstream, in fault localization:
  the model doesn't know *which* method contains the bug once it's past
  the file hint.
