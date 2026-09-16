"""Thin wrappers around the defects4j CLI."""
import subprocess, shutil, os
from pathlib import Path
from dataclasses import dataclass

D4J = os.path.expanduser("~/btp/defects4j/framework/bin/defects4j")
JAVA_HOME = os.path.expanduser("~/miniconda3/envs/repairlam")
os.environ["JAVA_HOME"] = JAVA_HOME
os.environ["PATH"] = f"{JAVA_HOME}/bin:" + os.environ.get("PATH", "")


def _run(cmd, cwd=None, timeout=600):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, shell=isinstance(cmd, str))
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"TIMEOUT after {timeout}s"


@dataclass
class TestResult:
    passed: bool
    failing: list
    raw: str


def active_bugs(project: str) -> list:
    rc, out, err = _run([D4J, "query", "-p", project, "-q", "bug.id"])
    if rc != 0:
        raise RuntimeError(f"query failed: {err}")
    return [l.split(",")[0] for l in out.strip().splitlines() if l.strip()]


def checkout(project, bug, workdir) -> bool:
    if Path(workdir).exists():
        shutil.rmtree(workdir)
    rc, out, err = _run([D4J, "checkout", "-p", project,
                         "-v", f"{bug}b", "-w", str(workdir)], timeout=600)
    return rc == 0


def compile_project(workdir) -> tuple:
    rc, out, err = _run([D4J, "compile"], cwd=workdir, timeout=600)
    return rc == 0, (out + err)[-4000:]


def run_tests(workdir, timeout=900) -> TestResult:
    rc, out, err = _run([D4J, "test"], cwd=workdir, timeout=timeout)
    raw = out + err
    failing = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("- "):
            failing.append(line[2:].strip())
    return TestResult(passed=(rc == 0 and len(failing) == 0),
                      failing=failing, raw=raw[-4000:])


def export(workdir, prop) -> str:
    rc, out, err = _run([D4J, "export", "-p", prop], cwd=workdir, timeout=300)
    lines = [l for l in out.strip().splitlines()
             if l.strip() and not l.startswith("Running ant")]
    return lines[-1].strip() if lines else ""


def buggy_file(workdir) -> Path:
    """Oracle localisation: the file the developer actually changed."""
    cls = export(workdir, "classes.modified").split()[0]
    src = export(workdir, "dir.src.classes")
    return Path(workdir) / src / (cls.replace(".", "/") + ".java")


def cleanup(workdir):
    if Path(workdir).exists():
        shutil.rmtree(workdir, ignore_errors=True)
