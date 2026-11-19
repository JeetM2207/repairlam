import subprocess

path = "/home/23ucs603/btp/repairlam/github_workspaces/seed/gson_600/gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java"
with open(path) as f:
    c = f.read()

old_part = """          in.beginArray();
          while (in.hasNext()) {
            try {"""

new_part = """          in.beginArray();
          while (in.hasNext()) {
            if (in.peek() == JsonToken.NULL) {
              throw new JsonSyntaxException(
                  "null is not a valid AtomicIntegerArray element; at path " + in.getPath());
            }
            try {"""

assert old_part in c, "old_part not found"
with open(path, "w") as f:
    f.write(c.replace(old_part, new_part, 1))

_JDK21_HOME = "/home/23ucs603/miniconda3/envs/jdk21tools"
_MVN = "/home/23ucs603/miniconda3/envs/repairlam/bin/mvn"
cmd = ["env", f"JAVA_HOME={_JDK21_HOME}",
       f"PATH={_JDK21_HOME}/bin:/home/23ucs603/miniconda3/envs/repairlam/bin:/usr/bin:/bin",
       _MVN, "-q", "-pl", "gson", "-am", "-Dtest=AtomicIntegerArrayNull3047Test", "test"]

p = subprocess.run(cmd, cwd="/home/23ucs603/btp/repairlam/github_workspaces/seed/gson_600", capture_output=True, text=True)
print("With in.getPath() return code:", p.returncode)
print("=== STDOUT ===")
print(p.stdout)
print("=== STDERR ===")
print(p.stderr)

subprocess.run(["git", "checkout", "--", path], cwd="/home/23ucs603/btp/repairlam/github_workspaces/seed/gson_600")
