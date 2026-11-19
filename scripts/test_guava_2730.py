import subprocess

workdir = "/home/23ucs603/btp/repairlam/github_workspaces/seed/guava_3790"
test_file = workdir + "/guava-tests/test/com/google/common/util/concurrent/RateLimiterZeroWarmup2730Test.java"

content = """package com.google.common.util.concurrent;

import static org.junit.Assert.assertTrue;
import java.util.concurrent.TimeUnit;
import org.junit.Test;

public class RateLimiterZeroWarmup2730Test {
  @Test
  public void testWarmUpWithZeroWarmupAndRealClock() {
    RateLimiter limiter = RateLimiter.create(50.0, 0, TimeUnit.SECONDS);
    int totalPermits = 100;
    double totalSleep = 0;
    for (int i = 0; i < totalPermits; i++) {
      totalSleep += limiter.acquire();
    }
    assertTrue("Expected totalSleep > 0.5s for 100 permits at 50/s, but got " + totalSleep, totalSleep > 0.5);
  }
}
"""

with open(test_file, "w") as f:
    f.write(content)

cmd = ["mvn", "-q", "-pl", "guava-tests", "-am", "-Dtest=RateLimiterZeroWarmup2730Test", "test"]
p = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True)
print("Return code:", p.returncode)
print("Output:\n", (p.stdout + p.stderr)[-3000:])
