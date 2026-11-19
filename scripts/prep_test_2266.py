import subprocess

test_script = """
import subprocess
from pathlib import Path

workdir = Path("/tmp/jsoup_test")
test_file = workdir / "src/test/java/org/jsoup/nodes/DocumentTest.java"

text = test_file.read_text()
test_method = '''
    @Test void emptyXmlDocCharsetOutOfBounds2266() {
        org.jsoup.nodes.Document xml = new org.jsoup.nodes.Document(org.jsoup.parser.Parser.NamespaceXml, "https://example.com");
        xml.outputSettings().syntax(org.jsoup.nodes.Document.OutputSettings.Syntax.xml);
        xml.charset(java.nio.charset.StandardCharsets.UTF_8);
    }
'''
if "emptyXmlDocCharsetOutOfBounds2266" not in text:
    # insert before last closing brace
    idx = text.rfind("}")
    test_file.write_text(text[:idx] + test_method + "\\n}\\n")

cmd = ["env", "JAVA_HOME=/home/23ucs603/miniconda3/envs/jdk21tools",
       "PATH=/home/23ucs603/miniconda3/envs/jdk21tools/bin:/home/23ucs603/miniconda3/envs/repairlam/bin:/usr/bin:/bin",
       "/home/23ucs603/miniconda3/envs/repairlam/bin/mvn", "-q", "-Dtest=DocumentTest#emptyXmlDocCharsetOutOfBounds2266", "test"]

p = subprocess.run(cmd, cwd=str(workdir), capture_output=True, text=True)
print("Return code:", p.returncode)
print("Output:\\n", (p.stdout + p.stderr)[-2000:])
"""

open("scripts/run_test_2266.py", "w").write(test_script)
print("Wrote scripts/run_test_2266.py")
