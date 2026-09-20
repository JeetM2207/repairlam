"""End-to-end pipeline: read a GitHub issue, clone the repo, run the FSM
repair loop against it, then either open a PR (PLAUSIBLE) or post the
escalation/timeout report as an issue comment.

Deliberately separate from repairlam.agent.loop's `run_bug`/`main` (the
Defects4j harness) -- this module owns its own workdir, its own checkout
logic (git, not `defects4j checkout`), and its own outcome handling (PR/
comment, not a results JSON). It reuses only what's generic: the FSM core
(`run_fsm_core`), the Dispatcher, and the LLM call helper (`ask`).
"""
import os
import time
from pathlib import Path

from repairlam.events import EventLog
from repairlam.tools.registry import Dispatcher
from repairlam.agent.loop import run_fsm_core, ask, server_ctx, MODEL
from repairlam.github.issue_client import GithubClient
from repairlam.github.repo_env import RepoEnv

BTP = os.path.expanduser("~/btp")
WORK = f"{BTP}/repairlam/github_workspaces"
LOGS = f"{BTP}/repairlam/logs"

COMMIT_AUTHOR_NAME = "repairlam-bot"
COMMIT_AUTHOR_EMAIL = "repairlam-bot@users.noreply.github.com"


def _issue_context(issue) -> str:
    body = (issue.body or "").strip()
    return (f"GitHub issue #{issue.number}: {issue.title}\n\n"
            f"{body}" if body else f"GitHub issue #{issue.number}: {issue.title}")


def _generate_commit_message(ctx, issue, diff_text) -> str:
    """One extra LLM call: a short, conventional commit message for the
    actual diff produced, grounded in the issue it closes."""
    sysmsg = ("You write concise, conventional git commit messages. Reply "
              "with ONLY the commit message -- a one-line summary (max 72 "
              "chars, imperative mood, no trailing period), then a blank "
              "line, then 1-3 sentences explaining the fix if useful. No "
              "markdown, no quotes around it.")
    user = (f"Issue #{issue.number}: {issue.title}\n\n{issue.body or ''}\n\n"
            f"--- diff ---\n{diff_text[:6000]}\n--- end diff ---\n\n"
            f"Write the commit message for this fix.")
    try:
        text, _, _, _ = ask([{"role": "system", "content": sysmsg},
                            {"role": "user", "content": user}], 200)
        text = text.strip()
        return text if text else f"Fix #{issue.number}: {issue.title}"
    except Exception:
        return f"Fix #{issue.number}: {issue.title}"


def _escalation_report(issue, outcome, escalation, edits_applied) -> str:
    header = {
        "ESCALATED": "🤖 repairlam attempted this issue and escalated.",
        "TIMEOUT": "🤖 repairlam attempted this issue and ran out of turns without a fix.",
        "FAILED": "🤖 repairlam attempted this issue but its fix didn't pass tests.",
    }.get(outcome, f"🤖 repairlam attempted this issue (outcome: {outcome}).")
    body = [header, "", f"Edits attempted: {edits_applied}"]
    if escalation:
        body += ["", "**Reason:**", str(escalation)[:2000]]
    body += ["", "_No pull request was opened. This comment was posted "
                  "automatically; a human should take it from here._"]
    return "\n".join(body)


def run_on_issue(repo_full_name, issue_number, token, test_cmd,
                 build_cmd=None, target_test_cmd=None, base_branch="main",
                 dry_run=False, client=None):
    """Full pipeline for one issue. Returns a dict with the outcome and
    whatever artifact was produced (pr_url or comment posted).

    dry_run=True runs the FSM and computes everything a real run would
    produce, but never calls the GitHub write APIs (push/PR/comment) --
    used for local validation before pointing this at anything real.

    `client`, if given, is used instead of constructing a real
    GithubClient(token) -- lets tests inject a fake/mock client (any
    object exposing get_issue/post_comment/create_pull_request/
    clone_url) without a real token or network access.
    """
    client = client if client is not None else (GithubClient(token) if token else None)
    if client is None:
        raise RuntimeError("no client and no token given -- run_on_issue "
                            "needs one or the other")
    issue = client.get_issue(repo_full_name, issue_number)

    run_id = f"{repo_full_name.replace('/', '_')}_issue{issue_number}_{time.strftime('%Y%m%dT%H%M%S')}"
    log = EventLog(run_id, LOGS)
    workdir = f"{WORK}/{run_id}"
    branch = f"repairlam/issue-{issue_number}"

    env = RepoEnv(test_cmd=test_cmd, build_cmd=build_cmd,
                  target_test_cmd=target_test_cmd)
    bug_id = f"{repo_full_name}#{issue_number}"
    print(f"\n=== {bug_id} ===", flush=True)

    try:
        clone_url = client.clone_url(repo_full_name)
        if not env.clone_and_branch(clone_url, base_branch, branch, workdir):
            log.summary(bug_id, "ERROR", model=MODEL, note="clone/branch failed")
            return {"outcome": "ERROR", "note": "clone/branch failed"}

        ok, out = env.compile_project(workdir)
        if not ok:
            log.summary(bug_id, "ERROR", model=MODEL, note="build failed")
            return {"outcome": "ERROR", "note": f"build failed: {out[:300]}"}

        initial = env.run_tests(workdir, timeout=600)
        if initial.passed:
            log.summary(bug_id, "ERROR", model=MODEL,
                       note="no failing test found at HEAD; nothing to repair")
            return {"outcome": "ERROR", "note": "no failing test at HEAD"}

        disp = Dispatcher(workdir, log, bug_id, trigger_class=None,
                          hint_file=None, env=env)
        disp.last_test = initial

        ctx = server_ctx()
        outcome, escalation, attempts = run_fsm_core(
            disp, ctx, hint_file=None, log=log, bug_id=bug_id, env=env,
            extra_context=_issue_context(issue))

        summary = log.summary(bug_id, outcome, model=MODEL,
                              edits_applied=len(disp.edits),
                              fix_attempts=attempts, escalation=escalation)
        print(f"  -> {outcome} ({len(disp.edits)} edits)", flush=True)

        if outcome == "PLAUSIBLE":
            diff_text = env.diff(workdir)
            msg = _generate_commit_message(ctx, issue, diff_text)
            title = msg.splitlines()[0] if msg else f"Fix #{issue.number}"
            pr_body = (f"Closes #{issue.number}.\n\n{msg}\n\n"
                      f"_Opened automatically by repairlam after a "
                      f"PLAUSIBLE fix ({attempts} edit attempt(s))._")
            if dry_run:
                print("  [dry_run] would commit, push, and open PR:")
                print(f"  title: {title}")
                print(f"  diff:\n{diff_text[:2000]}")
                return {"outcome": outcome, "dry_run": True, "commit_message": msg,
                       "diff": diff_text, "summary": summary}
            if not env.commit_and_push(workdir, branch, msg,
                                       COMMIT_AUTHOR_NAME, COMMIT_AUTHOR_EMAIL):
                return {"outcome": outcome, "note": "commit/push failed",
                       "summary": summary}
            pr = client.create_pull_request(repo_full_name, branch,
                                            base_branch, title, pr_body)
            return {"outcome": outcome, "pr_url": pr.html_url, "summary": summary}

        # ESCALATED, TIMEOUT, or FAILED -- post the report as a comment
        report = _escalation_report(issue, outcome, escalation, len(disp.edits))
        if dry_run:
            print("  [dry_run] would post comment:")
            print(f"  {report}")
            return {"outcome": outcome, "dry_run": True, "comment": report,
                   "summary": summary}
        client.post_comment(repo_full_name, issue_number, report)
        return {"outcome": outcome, "comment_posted": True, "summary": summary}

    except Exception as e:
        log.summary(bug_id, "ERROR", model=MODEL, note=str(e)[:300])
        print(f"  -> ERROR {str(e)[:200]}", flush=True)
        return {"outcome": "ERROR", "note": str(e)[:300]}
    finally:
        env.cleanup(workdir)
