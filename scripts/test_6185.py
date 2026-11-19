import os
import subprocess
from pathlib import Path

workdir = Path("/home/23ucs603/btp/repairlam/github_workspaces/seed/jackson-databind_6185")
test_file = workdir / "src/test/java/com/fasterxml/jackson/databind/ser/jdk/InetSocketAddressIPv6Unresolved6185Test.java"

content = """package com.fasterxml.jackson.databind.ser.jdk;

import java.io.IOException;
import java.net.InetSocketAddress;
import org.junit.jupiter.api.Test;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.testutil.DatabindTestUtil;

public class InetSocketAddressIPv6Unresolved6185Test extends DatabindTestUtil {
    private final ObjectMapper MAPPER = new ObjectMapper();

    @Test
    public void testInetSocketAddressIPv6Unresolved() throws IOException {
        String s = MAPPER.writeValueAsString(InetSocketAddress.createUnresolved("2001:db8::1", 443));
        System.out.println("ACTUAL VALUE: " + s);
        throw new RuntimeException("ACTUAL VALUE: " + s);
    }
}
"""
test_file.write_text(content)
env = os.environ.copy()
env["PATH"] = "/home/23ucs603/miniconda3/envs/repairlam/bin:" + env.get("PATH", "")

p = subprocess.run(["mvn", "test-compile"], cwd=str(workdir), capture_output=True, text=True, env=env)
print("Compile rc:", p.returncode)
p_test = subprocess.run(["mvn", "-Dtest=InetSocketAddressIPv6Unresolved6185Test", "test"],
                        cwd=str(workdir), capture_output=True, text=True, env=env)
print("Test rc:", p_test.returncode)
for line in p_test.stdout.splitlines():
    if "ACTUAL VALUE" in line or "FAILURE" in line or "ERROR" in line or "Tests run" in line:
        print(line)
