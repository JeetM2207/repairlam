import subprocess

path = "/home/23ucs603/btp/repairlam/github_workspaces/seed/gson_600/gson/src/test/java/com/google/gson/functional/JavaUtilConcurrentAtomicTest.java"

with open(path) as f:
    code = f.read()

# restore clean state first if needed
if "testAtomicIntegerArrayWithNullElement" in code:
    subprocess.run(["git", "checkout", "--", path], cwd="/home/23ucs603/btp/repairlam/github_workspaces/seed/gson_600")
    with open(path) as f:
        code = f.read()

idx = code.rfind("}")
new_test = """
  @Test
  public void testAtomicIntegerArrayWithNullElement() {
    JsonSyntaxException e =
        assertThrows(
            JsonSyntaxException.class, () -> gson.fromJson("[1,null,3]", AtomicIntegerArray.class));
    assertThat(e)
        .hasMessageThat()
        .isEqualTo("null is not a valid AtomicIntegerArray element; at path $[1]");
  }
}
"""

with open(path, "w") as f:
    f.write(code[:idx] + new_test)

cmd = ["env", "JAVA_HOME=/home/23ucs603/miniconda3/envs/jdk21tools",
       "PATH=/home/23ucs603/miniconda3/envs/jdk21tools/bin:/home/23ucs603/miniconda3/envs/repairlam/bin:/usr/bin:/bin",
       "/home/23ucs603/miniconda3/envs/repairlam/bin/mvn", "-pl", "gson", "-Dtest=JavaUtilConcurrentAtomicTest#testAtomicIntegerArrayWithNullElement", "test"]

p = subprocess.run(cmd, cwd="/home/23ucs603/btp/repairlam/github_workspaces/seed/gson_600", capture_output=True, text=True)
print("Return code:", p.returncode)
for l in (p.stdout + p.stderr).splitlines():
    if "FAILURE" in l or "expected:" in l or "but was" in l or "Tests run:" in l or "ERROR" in l:
        print(l)
