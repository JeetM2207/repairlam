"""Thin wrappers around the defects4j CLI, with safe process-group timeouts."""
import subprocess, shutil, os, signal
from pathlib import Path
from dataclasses import dataclass

D4J = os.path.expanduser("~/btp/defects4j/framework/bin/defects4j")
JAVA_HOME = os.path.expanduser("~/miniconda3/envs/repairlam")
os.environ["JAVA_HOME"] = JAVA_HOME
os.environ["PATH"] = f"{JAVA_HOME}/bin:" + os.environ.get("PATH", "")


def _run(cmd, cwd=None, timeout=600):
    """Kill the WHOLE process group on timeout, so no orphaned java/ant
    child survives. Orphans are what silently slowed every later run."""
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True,
                         start_new_session=True)
    try:
        out, err = p.communicate(timeout=timeout)
        return p.returncode, out, err
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            out, err = p.communicate(timeout=5)
        except Exception:
            out, err = "", ""
        return -1, out, f"TIMEOUT after {timeout}s\n{err}"


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


def compile_project(workdir, timeout=300) -> tuple:
    rc, out, err = _run([D4J, "compile"], cwd=workdir, timeout=timeout)
    return rc == 0, (out + err)[-4000:]


def run_tests(workdir, timeout=600, test_class=None) -> TestResult:
    """test_class (e.g. 'org.foo.BarTest') runs only that class via
    'defects4j test -t' -- much faster for in-loop feedback. Always
    confirm with an unfiltered call before accepting a fix as plausible."""
    cmd = [D4J, "test"]
    if test_class:
        cmd += ["-t", test_class]
    rc, out, err = _run(cmd, cwd=workdir, timeout=timeout)
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
