from pathlib import Path

csv_format_file = Path("/tmp/csv_test/src/main/java/org/apache/commons/csv/CSVFormat.java")
text = csv_format_file.read_text()
if "isCommentMarkerSet() && c == commentMarker.charValue()" in text:
    print("Fix is ALREADY present in CSVFormat.java")
else:
    print("Fix is NOT present in CSVFormat.java (Bug is PRESENT!)")

csv_printer_test = Path("/tmp/csv_test/src/test/java/org/apache/commons/csv/CSVPrinterTest.java")
test_text = csv_printer_test.read_text()
if "testQuoteCommentMarkerFirstChar" in test_text:
    print("testQuoteCommentMarkerFirstChar is ALREADY present in CSVPrinterTest.java")
else:
    print("testQuoteCommentMarkerFirstChar is NOT present in CSVPrinterTest.java")
