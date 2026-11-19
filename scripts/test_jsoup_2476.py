import subprocess
from pathlib import Path

workdir = Path("/tmp/jsoup_test")
test_file = workdir / "src/test/java/org/jsoup/safety/CleanerTest.java"

text = test_file.read_text()
test_method = """
    @org.junit.jupiter.api.Test
    void testCleanerEnforcedAttrPreserveCase2476() {
        org.jsoup.nodes.Document dirty = org.jsoup.Jsoup.parse("<a REL='external'>One</a>", "",
            org.jsoup.parser.Parser.htmlParser().settings(org.jsoup.parser.ParseSettings.preserveCase));
        org.jsoup.safety.Cleaner cleaner = new org.jsoup.safety.Cleaner(org.jsoup.safety.Safelist.none()
            .addTags("a")
            .addEnforcedAttribute("a", "rel", "external"));

        String cleanHtml = cleaner.clean(dirty).body().html();
        org.junit.jupiter.api.Assertions.assertEquals("<a rel=\\"external\\">One</a>", cleanHtml);
    }
"""

if "testCleanerEnforcedAttrPreserveCase2476" not in text:
    idx = text.rfind("}")
    test_file.write_text(text[:idx] + test_method + "\n}\n")

cmd = ["env", "JAVA_HOME=/home/23ucs603/miniconda3/envs/jdk21tools",
       "PATH=/home/23ucs603/miniconda3/envs/jdk21tools/bin:/home/23ucs603/miniconda3/envs/repairlam/bin:/usr/bin:/bin",
       "/home/23ucs603/miniconda3/envs/repairlam/bin/mvn", "-q", "-Dtest=CleanerTest#testCleanerEnforcedAttrPreserveCase2476", "test"]

p = subprocess.run(cmd, cwd=str(workdir), capture_output=True, text=True)
print("Return code:", p.returncode)
print("Output:\n", (p.stdout + p.stderr)[-3000:])
