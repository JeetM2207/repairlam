import subprocess

workdir = "/home/23ucs603/btp/repairlam/github_workspaces/seed/guava_3790"
test_file = workdir + "/guava-tests/test/com/google/common/collect/ImmutableClassToInstanceMap8693Test.java"

content = """package com.google.common.collect;

import static org.junit.Assert.assertEquals;
import java.io.ObjectStreamClass;
import org.junit.Test;

// https://github.com/google/guava/issues/8693:
// ImmutableClassToInstanceMap is missing an explicit serialVersionUID = 0,
// causing serialization incompatibility across Guava releases.
public class ImmutableClassToInstanceMap8693Test {
  @Test
  public void testSerialVersionUIDMatchesMutableVersion() {
    long actualUid = ObjectStreamClass.lookup(ImmutableClassToInstanceMap.class).getSerialVersionUID();
    assertEquals("ImmutableClassToInstanceMap must declare serialVersionUID = 0 to ensure stable serialization", 0L, actualUid);
  }
}
"""

with open(test_file, "w") as f:
    f.write(content)

MAVEN_NO_FAIL_IF_NO_TESTS = "-Dsurefire.failIfNoSpecifiedTests=false"
cmd = ["mvn", "-q", "-pl", "guava-tests", "-am", "-Dtest=ImmutableClassToInstanceMap8693Test",
       MAVEN_NO_FAIL_IF_NO_TESTS, "test"]
p = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True)
print("Return code:", p.returncode)
print("Output:\n", (p.stdout + p.stderr)[-3000:])
