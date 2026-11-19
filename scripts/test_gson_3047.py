test_code = """package com.google.gson.functional;

import static org.junit.Assert.assertThrows;
import com.google.gson.Gson;
import com.google.gson.JsonSyntaxException;
import java.util.concurrent.atomic.AtomicIntegerArray;
import org.junit.Test;

public class AtomicIntegerArrayNull3047Test {
  @Test
  public void testAtomicIntegerArrayNullElementThrowsJsonSyntaxException() {
    Gson gson = new Gson();
    assertThrows(JsonSyntaxException.class, () ->
        gson.fromJson("[1,null,3]", AtomicIntegerArray.class)
    );
  }
}
"""

with open("/home/23ucs603/btp/repairlam/github_workspaces/seed/gson_600/gson/src/test/java/com/google/gson/functional/AtomicIntegerArrayNull3047Test.java", "w") as f:
    f.write(test_code)

import subprocess
_JDK21_HOME = "/home/23ucs603/miniconda3/envs/jdk21tools"
_MVN = "/home/23ucs603/miniconda3/envs/repairlam/bin/mvn"
cmd = ["env", f"JAVA_HOME={_JDK21_HOME}",
       f"PATH={_JDK21_HOME}/bin:/home/23ucs603/miniconda3/envs/repairlam/bin:/usr/bin:/bin",
       _MVN, "-q", "-pl", "gson", "-am", "-Dtest=AtomicIntegerArrayNull3047Test", "test"]

p = subprocess.run(cmd, cwd="/home/23ucs603/btp/repairlam/github_workspaces/seed/gson_600", capture_output=True, text=True)
print("Return code:", p.returncode)
print("Output:\n", (p.stdout + p.stderr)[-3000:])
