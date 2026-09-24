"""Repeatable orchestration of the process validated live on
google/guava#3493 -> JeetM2207/guava#1/PR#2: fork a repo if needed, seed a
regression test that reproduces a real, currently-open issue, verify it
actually fails against current (buggy) code, push it, open the issue on the
fork with the original text plus a credit note, run the live FSM pipeline
against it, and log the outcome.

Deliberately NOT a "just give me any repo+issue and I'll figure out the
rest" black box: writing a *correct* regression test requires understanding
each specific bug (what input reproduces it, what the correct output/
behavior actually is). That understanding has to come from a human/agent
reading the real issue -- it can't be derived generically. So the unit of
work here is a `BugSpec`: the mechanical steps (fork, seed, verify-fails,
push, open issue, run pipeline, log) are fully automated and reusable;
the *content* of the regression test is supplied per bug, the same way it
was written by hand for the guava run.

Resumable by design: every attempt (including SKIPPED/ERROR) is appended to
results/live_run_log.json immediately after it finishes, and `main()` skips
any BugSpec whose key is already present in that log -- so an interrupted
batch (session/usage limit) picks back up automatically on the next run
without redoing or re-reporting completed bugs.
"""
import json
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from repairlam.github.issue_client import GithubClient
from repairlam.github.repo_env import _run, git_auth_env
from repairlam.github import pipeline

ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT / "results" / "live_run_log.json"
WORK = ROOT / "github_workspaces" / "seed"

# Modern repos (Gson 2.14+, Jackson 3.x) require JDK 17+ or 21.
# If a dedicated modern JDK exists on the host, configure it.
for _jdk in [
    Path("/home/23ucs603/miniconda3/envs/jdk21tools"),
    Path("/usr/lib/jvm/java-21-openjdk"),
    Path("/usr/lib/jvm/java-17-openjdk"),
]:
    if _jdk.exists():
        import os
        os.environ["JAVA_HOME"] = str(_jdk)
        os.environ["PATH"] = f"{_jdk}/bin:{os.environ.get('PATH', '')}"
        break


@dataclass
class BugSpec:
    key: str                      # unique id, e.g. "guava#3493"
    source_repo: str              # upstream repo the bug is sourced from, e.g. "google/guava"
    source_issue_number: int      # issue number on the UPSTREAM repo
    test_cmd: list                # argv to run the module/class-scoped test (module build + test)
    base_branch: str = "master"
    build_cmd: list = None
    target_test_cmd: object = None  # callable(test_class:str) -> argv, passed through to RepoEnv
    # Either (test_file, test_insert_after, test_method) to edit an existing file at a
    # unique anchor, or (new_test_file, new_test_file_content) to write a whole new file.
    test_file: str = None                # path (relative to repo root) of the test file to edit
    test_insert_after: str = None        # anchor string; must occur exactly once in test_file
    test_method: str = None              # Java source of the new test method to insert after the anchor
    new_test_file: str = None            # path of a brand-new test file to create instead
    new_test_file_content: str = None    # full content for new_test_file


def _load_log():
    if LOG_PATH.exists():
        return json.loads(LOG_PATH.read_text())
    return {"runs": []}


def _save_log(log):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(log, indent=2))


def _append_result(entry):
    log = _load_log()
    log["runs"] = [r for r in log["runs"] if r["key"] != entry["key"]]
    log["runs"].append(entry)
    _save_log(log)
    return log


def _already_done(spec_key):
    log = _load_log()
    return any(r["key"] == spec_key and r["outcome"] not in ("ERROR",)
              for r in log["runs"])


def _insert_test(workdir: Path, spec: BugSpec):
    if spec.new_test_file:
        path = workdir / spec.new_test_file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(spec.new_test_file_content)
        return
    path = workdir / spec.test_file
    text = path.read_text()
    n = text.count(spec.test_insert_after)
    if n != 1:
        raise RuntimeError(f"anchor found {n} times in {spec.test_file}, "
                           f"expected exactly 1")
    path.write_text(text.replace(spec.test_insert_after,
                                 spec.test_insert_after + "\n\n" + spec.test_method,
                                 1))


def _seed_and_verify(client, spec: BugSpec, fork_full, workdir: Path):
    """Clones the fork's base branch, inserts the regression test, and runs
    it. Returns (still_buggy: bool, raw_test_output: str). Leaves the clone
    on disk (caller pushes it if still_buggy)."""
    if workdir.exists():
        import shutil
        shutil.rmtree(workdir)
    clone_url = client.clone_url(fork_full)
    rc, out, err = _run(["git", "clone", "--depth", "1", "--branch",
                         spec.base_branch, clone_url, str(workdir)],
                        timeout=300, extra_env=git_auth_env())
    if rc != 0:
        raise RuntimeError(f"clone failed: {(out + err)[-1000:]}")

    _insert_test(workdir, spec)

    if spec.build_cmd:
        rc, out, err = _run(spec.build_cmd, cwd=str(workdir), timeout=600)
        if rc != 0:
            raise RuntimeError(f"build failed: {(out + err)[-2000:]}")

    rc, out, err = _run(spec.test_cmd, cwd=str(workdir), timeout=600)
    raw = out + err
    return rc != 0, raw[-4000:]


def _push_to_base(workdir: Path, base_branch: str, message: str):
    """Idempotent: a re-run against a bug whose regression test was already
    committed to base_branch by an earlier attempt has nothing new to stage
    -- that's success (the desired state already holds), not an error."""
    _run(["git", "add", "-A"], cwd=str(workdir), timeout=60)
    rc, out, err = _run(["git", "diff", "--cached", "--name-only"],
                        cwd=str(workdir), timeout=30)
    if out.strip():
        rc, out, err = _run(["git", "-c", "user.name=repairlam-bot",
                             "-c", "user.email=repairlam-bot@users.noreply.github.com",
                             "commit", "-m", message], cwd=str(workdir), timeout=60)
        if rc != 0:
            raise RuntimeError(f"commit failed: {(out + err)[-1000:]}")
    rc, out, err = _run(["git", "push", "origin", base_branch], cwd=str(workdir),
                        timeout=120, extra_env=git_auth_env())
    if rc != 0:
        raise RuntimeError(f"push failed: {(out + err)[-1000:]}")


def run_bug_spec(spec: BugSpec, token: str) -> dict:
    """Runs the full seed->issue->pipeline flow for one BugSpec and appends
    the outcome to results/live_run_log.json. Returns the log entry."""
    print(f"\n########## {spec.key} ##########", flush=True)
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    entry = {"key": spec.key, "source_repo": spec.source_repo,
             "source_issue_number": spec.source_issue_number,
             "started": started, "outcome": "ERROR"}
    try:
        client = GithubClient(token)
        source_issue = client.get_issue(spec.source_repo, spec.source_issue_number)

        fork_full = client.ensure_fork(spec.source_repo)
        entry["fork"] = fork_full
        print(f"  fork: {fork_full}", flush=True)

        workdir = WORK / spec.key.replace("/", "_").replace("#", "_")
        still_buggy, raw = _seed_and_verify(client, spec, fork_full, workdir)
        if not still_buggy:
            entry["outcome"] = "SKIPPED"
            entry["note"] = "regression test passed against current source -- bug appears already fixed upstream/in fork"
            print("  bug not reproducible -- SKIPPED", flush=True)
            return _append_result(entry)["runs"][-1]
        print("  regression test fails against current code -- bug confirmed present", flush=True)

        _push_to_base(workdir, spec.base_branch,
                      f"Add regression test for {spec.source_repo}#{spec.source_issue_number}")
        print("  pushed regression test to fork", flush=True)

        client.ensure_issues_enabled(fork_full)

        credit = (f"\n\n---\n_Sourced from {spec.source_repo}#"
                 f"{spec.source_issue_number}: {source_issue.url}_")
        new_issue = client.create_issue(fork_full, source_issue.title,
                                        (source_issue.body or "") + credit)
        entry["issue_url"] = new_issue.url
        print(f"  opened issue: {new_issue.url}", flush=True)

        result = pipeline.run_on_issue(
            fork_full, new_issue.number, token,
            test_cmd=spec.test_cmd, build_cmd=spec.build_cmd,
            target_test_cmd=spec.target_test_cmd, base_branch=spec.base_branch,
            client=client)

        entry["outcome"] = result.get("outcome")
        entry["pr_url"] = result.get("pr_url")
        entry["comment_posted"] = result.get("comment_posted")
        summ = result.get("summary") or {}
        entry["turns_used"] = summ.get("turns_used")
        entry["edits_applied"] = summ.get("edits_applied")
        entry["note"] = result.get("note")
        return _append_result(entry)["runs"][-1]

    except Exception as e:
        entry["outcome"] = "ERROR"
        entry["note"] = str(e)[:500]
        entry["traceback"] = traceback.format_exc()[-2000:]
        print(f"  -> ERROR: {str(e)[:300]}", flush=True)
        return _append_result(entry)["runs"][-1]


def main(specs, token, force_keys=None):
    """Runs every BugSpec in `specs` not already present with a non-ERROR
    outcome in results/live_run_log.json, one at a time, logging as it
    goes. Safe to interrupt and re-invoke with the same `specs` list.

    `force_keys`, if given, is a set of spec keys to re-run unconditionally
    (overwriting their prior log entry) even though already logged -- for
    correcting results that a fixed infrastructure bug invalidated."""
    force_keys = force_keys or set()
    for spec in specs:
        if spec.key not in force_keys and _already_done(spec.key):
            print(f"skip (already logged): {spec.key}", flush=True)
            continue
        run_bug_spec(spec, token)
    log = _load_log()
    counts = {}
    for r in log["runs"]:
        counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
    print("\n=== SUMMARY ===")
    print(json.dumps(counts, indent=2))
    return log


if __name__ == "__main__":
    import os
    import sys
    from repairlam.github.bug_specs import SPECS
    token = os.environ["GITHUB_TOKEN"]
    # optional: force-rerun specific keys, e.g.
    #   python -m repairlam.github.live_bug_pipeline gson#600 guava#3790
    force = set(sys.argv[1:]) if len(sys.argv) > 1 else None
    main(SPECS, token, force_keys=force)
