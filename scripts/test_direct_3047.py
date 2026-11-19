test_code = """package com.google.gson.functional;

import com.google.gson.Gson;
import java.util.concurrent.atomic.AtomicIntegerArray;
import org.junit.Test;

@SuppressWarnings("all")
public class AtomicIntegerArrayNull3047Test {
  @Test
  public void testDirect() {
    try {
      AtomicIntegerArray arr = new Gson().fromJson("[1,null,3]", AtomicIntegerArray.class);
      System.out.println("TEST COMPLETED WITHOUT EXCEPTION, arr=" + arr);
    } catch (Throwable e) {
      System.out.println("CAUGHT EXCEPTION: " + e.getClass().getName() + " -> " + e.getMessage());
      throw new RuntimeException("CAUGHT: " + e.getClass().getName(), e);
    }
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
       _MVN, "-pl", "gson", "-Dtest=AtomicIntegerArrayNull3047Test", "test"]

p = subprocess.run(cmd, cwd="/home/23ucs603/btp/repairlam/github_workspaces/seed/gson_600", capture_output=True, text=True)
print("Return code:", p.returncode)
for line in (p.stdout + p.stderr).splitlines():
    if "CAUGHT" in line or "FAILURE" in line or "ERROR" in line or "Exception" in line or "TEST COMPLETED" in line:
        print(line)
