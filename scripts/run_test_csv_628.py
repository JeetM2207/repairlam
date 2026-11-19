
import subprocess
from pathlib import Path

workdir = Path("/tmp/csv_test")
test_file = workdir / "src/test/java/org/apache/commons/csv/CSVRecordTest.java"

text = test_file.read_text()
test_method = '''
    @Test
    void testIsMappedNullWithIgnoreHeaderCase628() throws java.io.IOException {
        final CSVFormat format = CSVFormat.DEFAULT.builder().setHeader("A", "B").setIgnoreHeaderCase(true).get();
        try (CSVParser parser = CSVParser.parse("1,2", format)) {
            final CSVRecord record = parser.iterator().next();
            org.junit.jupiter.api.Assertions.assertFalse(record.isMapped(null));
            org.junit.jupiter.api.Assertions.assertFalse(record.isSet(null));
        }
    }
'''
if "testIsMappedNullWithIgnoreHeaderCase628" not in text:
    idx = text.rfind("}")
    test_file.write_text(text[:idx] + test_method + "\n}\n")

cmd = ["env", "JAVA_HOME=/home/23ucs603/miniconda3/envs/jdk21tools",
       "PATH=/home/23ucs603/miniconda3/envs/jdk21tools/bin:/home/23ucs603/miniconda3/envs/repairlam/bin:/usr/bin:/bin",
       "/home/23ucs603/miniconda3/envs/repairlam/bin/mvn", "-q", "-Dtest=CSVRecordTest#testIsMappedNullWithIgnoreHeaderCase628", "test"]

p = subprocess.run(cmd, cwd=str(workdir), capture_output=True, text=True)
print("Return code:", p.returncode)
print("Output:\n", (p.stdout + p.stderr)[-2000:])
