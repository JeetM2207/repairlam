test_code = """package com.google.gson.functional;

import static org.junit.Assert.assertEquals;
import com.google.gson.Gson;
import java.util.ArrayList;
import java.util.List;
import org.junit.Test;

@SuppressWarnings("all")
public class Gson754Test {
  static class R {
    List<B> blist;
  }
  static class B {
    int b = 1;
    List<R> rlist;
  }
  static class C extends B {
    int c = 2;
  }
  static class A {
    List<B> a;
  }

  @Test
  public void testPolymorphicCollectionSerializationWithCyclicReference() {
    Gson gson = new Gson();
    A a = new A();
    a.a = new ArrayList<>();
    a.a.add(new B());
    a.a.add(new C());
    String json = gson.toJson(a);
    assertEquals("{\\"a\\":[{\\"b\\":1},{\\"c\\":2,\\"b\\":1}]}", json);
  }
}
"""

with open("/home/23ucs603/btp/repairlam/github_workspaces/seed/gson_600/gson/src/test/java/com/google/gson/functional/Gson754Test.java", "w") as f:
    f.write(test_code)

import subprocess
_JDK21_HOME = "/home/23ucs603/miniconda3/envs/jdk21tools"
_MVN = "/home/23ucs603/miniconda3/envs/repairlam/bin/mvn"
cmd = ["env", f"JAVA_HOME={_JDK21_HOME}",
       f"PATH={_JDK21_HOME}/bin:/home/23ucs603/miniconda3/envs/repairlam/bin:/usr/bin:/bin",
       _MVN, "-q", "-pl", "gson", "-am", "-Dtest=Gson754Test", "-Dsurefire.failIfNoSpecifiedTests=false", "test"]

p = subprocess.run(cmd, cwd="/home/23ucs603/btp/repairlam/github_workspaces/seed/gson_600", capture_output=True, text=True)
print("Return code:", p.returncode)
print("Output:\n", (p.stdout + p.stderr)[-2000:])
