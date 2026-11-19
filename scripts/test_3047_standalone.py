import subprocess

test_code = """package com.google.gson.functional;

import static org.junit.Assert.assertThrows;
import static com.google.common.truth.Truth.assertThat;

import com.google.gson.Gson;
import com.google.gson.JsonSyntaxException;
import java.util.concurrent.atomic.AtomicIntegerArray;
import org.junit.Test;

@SuppressWarnings("all")
public class AtomicIntegerArrayNull3047Test {
  @Test
  public void testAtomicIntegerArrayWithNullElement() {
    JsonSyntaxException e =
        assertThrows(
            JsonSyntaxException.class, () -> new Gson().fromJson("[1,null,3]", AtomicIntegerArray.class));
    assertThat(e)
        .hasMessageThat()
        .isEqualTo("null is not a valid AtomicIntegerArray element; at path $[1]");
  }
}
"""

with open("/home/23ucs603/btp/repairlam/github_workspaces/seed/gson_600/gson/src/test/java/com/google/gson/functional/AtomicIntegerArrayNull3047Test.java", "w") as f:
    f.write(test_code)

_JDK21_HOME = "/home/23ucs603/miniconda3/envs/jdk21tools"
_MVN = "/home/23ucs603/miniconda3/envs/repairlam/bin/mvn"
cmd = ["env", f"JAVA_HOME={_JDK21_HOME}",
       f"PATH={_JDK21_HOME}/bin:/home/23ucs603/miniconda3/envs/repairlam/bin:/usr/bin:/bin",
       _MVN, "-q", "-pl", "gson", "-am", "-Dtest=AtomicIntegerArrayNull3047Test", "test"]

p = subprocess.run(cmd, cwd="/home/23ucs603/btp/repairlam/github_workspaces/seed/gson_600", capture_output=True, text=True)
print("Return code:", p.returncode)
for line in (p.stdout + p.stderr).splitlines():
    if "FAILURE" in line or "expected:" in line or "but was" in line or "Tests run:" in line:
        print(line)
