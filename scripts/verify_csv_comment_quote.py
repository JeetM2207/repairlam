import subprocess
from pathlib import Path

workdir = Path("/tmp/csv_test")
test_file = workdir / "src/test/java/org/apache/commons/csv/CSVPrinterTest.java"

text = test_file.read_text()
test_method = """
    @Test
    void testQuoteCommentMarkerFirstChar() throws IOException {
        final CSVFormat format = CSVFormat.DEFAULT.builder().setCommentMarker(';').get();
        final StringWriter sw = new StringWriter();
        final String col1 = ";comment-like";
        try (CSVPrinter printer = new CSVPrinter(sw, format)) {
            printer.printComment("a real comment");
            printer.printRecord(col1, "b");
            printer.printRecord("a;b", ";c");
        }
        final String string = sw.toString();
        assertEquals("; a real comment" + RECORD_SEPARATOR +
                "\\";comment-like\\",b" + RECORD_SEPARATOR +
                "a;b,\\";c\\"" + RECORD_SEPARATOR, string);
        try (CSVParser parser = CSVParser.parse(string, format)) {
            final java.util.List<CSVRecord> records = parser.getRecords();
            assertEquals(2, records.size());
            assertArrayEquals(new String[] {col1, "b"}, records.get(0).values());
            assertArrayEquals(new String[] {"a;b", ";c"}, records.get(1).values());
        }
    }
"""

if "testQuoteCommentMarkerFirstChar" not in text:
    idx = text.rfind("}")
    test_file.write_text(text[:idx] + test_method + "\n}\n")

_JDK21_HOME = "/home/23ucs603/miniconda3/envs/jdk21tools"
_MVN = "/home/23ucs603/miniconda3/envs/repairlam/bin/mvn"
cmd = ["env", f"JAVA_HOME={_JDK21_HOME}",
       f"PATH={_JDK21_HOME}/bin:/home/23ucs603/miniconda3/envs/repairlam/bin:/usr/bin:/bin",
       _MVN, "-q", "-Dtest=CSVPrinterTest#testQuoteCommentMarkerFirstChar", "test"]

p = subprocess.run(cmd, cwd=str(workdir), capture_output=True, text=True)
print("Return code:", p.returncode)
for l in (p.stdout + p.stderr).splitlines():
    if "FAILURE" in l or "expected:" in l or "but was" in l or "Tests run:" in l or "AssertionFailedError" in l:
        print(l)

subprocess.run(["git", "checkout", "--", str(test_file)], cwd=str(workdir))
