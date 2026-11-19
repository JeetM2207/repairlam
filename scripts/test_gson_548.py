import subprocess

workdir = "/home/23ucs603/btp/repairlam/github_workspaces/seed/gson_600"
test_file = workdir + "/gson/src/test/java/com/google/gson/functional/Gson548Test.java"

content = """package com.google.gson.functional;

import static org.junit.Assert.assertThrows;
import com.google.gson.Gson;
import com.google.gson.JsonIOException;
import java.io.IOException;
import java.io.Reader;
import org.junit.Test;

public class Gson548Test {
  @Test
  public void testIOExceptionWrappedInJsonIOException() {
    Gson gson = new Gson();
    Reader reader = new Reader() {
      @Override
      public int read(char[] cbuf, int off, int len) throws IOException {
        throw new IOException("disk error");
      }
      @Override
      public void close() {}
    };
    assertThrows(JsonIOException.class, () -> gson.fromJson(reader, Object.class));
  }
}
"""

with open(test_file, "w") as f:
    f.write(content)

_JDK21_HOME = "/home/23ucs603/miniconda3/envs/jdk21tools"
_MVN = "/home/23ucs603/miniconda3/envs/repairlam/bin/mvn"
cmd = ["env", f"JAVA_HOME={_JDK21_HOME}",
       f"PATH={_JDK21_HOME}/bin:/home/23ucs603/miniconda3/envs/repairlam/bin:/usr/bin:/bin",
       _MVN, "-q", "-pl", "gson", "-am", "-Dtest=Gson548Test", "test"]

p = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True)
print("Return code:", p.returncode)
print("Output:\n", (p.stdout + p.stderr)[-3000:])
