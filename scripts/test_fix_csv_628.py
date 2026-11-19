import subprocess

path = "/tmp/csv_test/src/main/java/org/apache/commons/csv/CSVRecord.java"
with open(path) as f:
    c = f.read()

old_part = "return headerMap != null && headerMap.containsKey(name);"
new_part = "return headerMap != null && name != null && headerMap.containsKey(name);"
assert old_part in c, "old_part not found in CSVRecord.java"

with open(path, "w") as f:
    f.write(c.replace(old_part, new_part, 1))

_JDK21_HOME = "/home/23ucs603/miniconda3/envs/jdk21tools"
_MVN = "/home/23ucs603/miniconda3/envs/repairlam/bin/mvn"
cmd = ["env", f"JAVA_HOME={_JDK21_HOME}",
       f"PATH={_JDK21_HOME}/bin:/home/23ucs603/miniconda3/envs/repairlam/bin:/usr/bin:/bin",
       _MVN, "-q", "-Dtest=CSVRecordTest#testIsMappedNullWithIgnoreHeaderCase628", "test"]

p = subprocess.run(cmd, cwd="/tmp/csv_test", capture_output=True, text=True)
print("CSV With fix return code:", p.returncode)
print("=== STDOUT ===")
print(p.stdout)
print("=== STDERR ===")
print(p.stderr)

subprocess.run(["git", "checkout", "--", path], cwd="/tmp/csv_test")
