# Edit quality analysis: model fix vs. developer fix

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

**Developer's actual fix** (`patches/1.src.patch`), in `createNumber`'s hex
branch, around line 464 — removes a leading-zero-stripping loop that was
throwing off the overflow check for hex literals:

```diff
         if (pfxLen > 0) { // we have a hex number
-            char firstSigDigit = 0; // strip leading zeroes
-            for(int i = pfxLen; i < str.length(); i++) {
-                firstSigDigit = str.charAt(i);
-                if (firstSigDigit == '0') { // count leading zeroes
-                    pfxLen++;
-                } else {
-                    break;
-                }
-            }
             final int hexDigits = str.length() - pfxLen;
-            if (hexDigits > 16 || (hexDigits == 16 && firstSigDigit > '7')) { // too many for Long
+            if (hexDigits > 16) { // too many for Long
                 return createBigInteger(str);
             }
-            if (hexDigits > 8 || (hexDigits == 8 && firstSigDigit > '7')) { // too many for an int
+            if (hexDigits > 8) { // too many for an int
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
plausible-looking Java, zero relationship to the hex-overflow off-by-one
that the test actually exercises. It got the right file purely from the
hint and then searched the wrong 50 lines of a 1400-line file for the rest
of the run.

---

## Lang-5 — `LocaleUtils.java`

**Developer's actual fix** (`patches/5.src.patch`), in `toLocale(String)` —
deletes an entire 20-line special-case branch for underscore-prefixed
locale strings (lines 94-119) that was mishandling malformed input:

```diff
         final char ch0 = str.charAt(0);
-        if (ch0 == '_') {
-            if (len < 3) {
-                throw new IllegalArgumentException(...);
-            }
-            ... (18 more lines of the '_' branch) ...
-            return new Locale("", str.substring(1, 3), str.substring(4));
-        } else {
             final char ch1 = str.charAt(1);
             ...
             return new Locale(str.substring(0, 2), str.substring(3, 5), str.substring(6));
-        }
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
is in, a few lines from the block that needs deleting. But it never
identifies that the `ch0 == '_'` branch is the problem; instead it toggles
argument counts on `Locale(...)` constructor calls back and forth across
two edits, net effect close to zero, then makes a change indistinguishable
from a no-op. It's rearranging deck chairs next to the actual bug rather
than removing it.

---

## Lang-20 — `StringUtils.java`

**Developer's actual fix** (`patches/20.src.patch`), in the `join(...)`
overloads — the `StringBuilder` initial capacity was computed as a
constant `noOfItems * 16` regardless of actual content, replaced with a
size derived from the first element:

```diff
-        StringBuilder buf = new StringBuilder(noOfItems * 16);
+        StringBuilder buf = new StringBuilder((array[startIndex] == null ? 16 : array[startIndex].toString().length()) + 1);
```
(and the same pattern in a second overload, with `+ separator.length()`)

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
- **No case involved removing buggy code.** All three real fixes are
  partly or wholly *deletions* (leading-zero loop, `_`-branch, hardcoded
  capacity formula). Every model edit was an *addition* or a small
  conditional tweak — the FSM's edit style (minimal, anchored, one
  `find`→`replace` at a time) makes large deletions structurally awkward
  to propose, which may itself be contributing to the miss.
- None of this is a parsing, anchor-matching, or tooling failure — by the
  time these edits landed, `apply_edit` had already verified the `find`
  text was real and unique. The gap is upstream, in fault localization:
  the model doesn't know *which* method contains the bug once it's past
  the file hint.
