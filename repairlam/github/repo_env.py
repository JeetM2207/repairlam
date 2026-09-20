"""Generic git+shell environment backend for a live repository, matching
the (compile_project, run_tests) interface repairlam.tools.registry.Dispatcher
expects -- same shape as repairlam.env.d4j but with no Defects4j dependency,
so the FSM core (repairlam.agent.loop.run_fsm_core) can run against either
unmodified.

Unlike Defects4j, a live repo has no oracle: no guaranteed pre-existing
failing test, no "which file changed" hint, no bug database. RepoEnv only
knows how to build and test whatever's checked out; the caller (pipeline.py)
is responsible for making sure a failing test exists before the FSM starts
(for the seeded-bug test repo, that's simply part of the seed).
"""
import os
import signal
import subprocess
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestResult:
    passed: bool
    failing: list
    raw: str


def _run(cmd, cwd=None, timeout=600):
    """Same safety property as repairlam.env.d4j._run: kill the whole
    process group on timeout so no orphaned child survives."""
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


_PYTEST_FAIL_RE = re.compile(r"^FAILED (\S+)", re.M)
_PYTEST_ERROR_RE = re.compile(r"^ERROR (\S+)", re.M)


def parse_pytest_failing(raw: str) -> list:
    """Failing test node ids from `pytest -v` / default output, e.g.
    'tests/test_foo.py::test_bar'. Used as the default failure parser;
    pass a different one to RepoEnv for other test runners."""
    return _PYTEST_FAIL_RE.findall(raw) + _PYTEST_ERROR_RE.findall(raw)


_MAVEN_FAIL_RE = re.compile(r"^\[ERROR\]\s+([\w.$]+\.\w+):\d+", re.M)


def parse_maven_failing(raw: str) -> list:
    """Failing test ids ('ClassName.methodName') from `mvn test`'s
    Surefire failure summary."""
    return _MAVEN_FAIL_RE.findall(raw)


def maven_target_test_cmd(test_class: str) -> list:
    """`test_class` here is a Surefire -Dtest expression: 'ClassName' or
    'ClassName#methodName'."""
    return ["mvn", "-q", f"-Dtest={test_class}", "test"]


class RepoEnv:
    """Configured per-repo: what command builds it (if any) and what
    command runs its tests. `test_cmd` and `build_cmd` are argv lists.
    `target_test_cmd(test_id)` builds a fast, single-test argv list for
    in-loop iteration; if not given, run_tests always runs the full suite
    (slower, but correct)."""

    def __init__(self, test_cmd, build_cmd=None, target_test_cmd=None,
                 failing_test_parser=parse_pytest_failing):
        self.test_cmd = test_cmd
        self.build_cmd = build_cmd
        self.target_test_cmd = target_test_cmd
        self.failing_test_parser = failing_test_parser

    def clone_and_branch(self, clone_url, base_branch, new_branch, workdir,
                         timeout=300) -> bool:
        """Clone `clone_url` (an https URL, may already have a token
        embedded by the caller -- never logged here) at `base_branch` into
        `workdir`, then create and check out `new_branch` from it."""
        if Path(workdir).exists():
            import shutil
            shutil.rmtree(workdir)
        rc, out, err = _run(["git", "clone", "--depth", "1", "--branch",
                             base_branch, clone_url, workdir], timeout=timeout)
        if rc != 0:
            return False
        rc, out, err = _run(["git", "checkout", "-b", new_branch],
                            cwd=workdir, timeout=60)
        return rc == 0

    def compile_project(self, workdir, timeout=300) -> tuple:
        if not self.build_cmd:
            return True, ""
        rc, out, err = _run(self.build_cmd, cwd=workdir, timeout=timeout)
        return rc == 0, (out + err)[-4000:]

    def run_tests(self, workdir, timeout=600, test_class=None) -> TestResult:
        cmd = self.test_cmd
        if test_class and self.target_test_cmd:
            cmd = self.target_test_cmd(test_class)
        rc, out, err = _run(cmd, cwd=workdir, timeout=timeout)
        raw = out + err
        failing = self.failing_test_parser(raw)
        return TestResult(passed=(rc == 0 and not failing), failing=failing,
                          raw=raw[-4000:])

    def diff(self, workdir) -> str:
        rc, out, err = _run(["git", "diff"], cwd=workdir, timeout=30)
        return out

    def commit_and_push(self, workdir, branch, message, author_name=None,
                        author_email=None, timeout=60) -> bool:
        env_kwargs = {}
        _run(["git", "add", "-A"], cwd=workdir, timeout=timeout)
        cmd = ["git"]
        if author_name and author_email:
            cmd += ["-c", f"user.name={author_name}",
                    "-c", f"user.email={author_email}"]
        rc, out, err = _run(cmd + ["commit", "-m", message], cwd=workdir,
                            timeout=timeout)
        if rc != 0:
            return False
        rc, out, err = _run(["git", "push", "-u", "origin", branch],
                            cwd=workdir, timeout=timeout)
        return rc == 0

    def cleanup(self, workdir):
        import shutil
        if Path(workdir).exists():
            shutil.rmtree(workdir, ignore_errors=True)
