"""Human-in-the-Loop Interactive Resumption Module.

Implements Module 5 & 8 from the thesis proposal:
Enables resuming an ESCALATED or TIMEOUT session from state REFLECT,
injecting developer guidance into the working context, and retrying
repair generation without restarting from scratch.
"""

import os
import json
import time
from pathlib import Path

from repairlam.agent.loop import run_fsm_core, server_ctx, MODEL
from repairlam.events import EventLog
from repairlam.tools.registry import Dispatcher
from repairlam.github.repo_env import RepoEnv, parse_maven_failing, parse_pytest_failing
from repairlam.github.issue_client import GithubClient
from repairlam.github.pipeline import (
    _issue_context,
    _generate_commit_message,
    _escalation_report,
    COMMIT_AUTHOR_NAME,
    COMMIT_AUTHOR_EMAIL,
    BTP,
    WORK,
    LOGS
)

def resume_from_feedback(repo_full_name, issue_number, token, developer_guidance,
                         test_cmd, build_cmd=None, target_test_cmd=None,
                         base_branch="main", max_turns=15):
    """Resume a previous repair attempt using developer feedback.

    The agent transitions from REFLECT to TRY_FIX with the human developer's
    hints appended to its recent working memory.
    """
    client = GithubClient(token)
    issue = client.get_issue(repo_full_name, issue_number)
    
    run_id = f"{repo_full_name.replace('/', '_')}_issue{issue_number}_resume_{time.strftime('%Y%m%dT%H%M%S')}"
    log = EventLog(run_id, LOGS)
    workdir = f"{WORK}/{run_id}"
    branch = f"repairlam/issue-{issue_number}-resume"
    bug_id = f"{repo_full_name}#{issue_number}"
    
    print(f"\n=== Resuming {bug_id} with Developer Guidance ===", flush=True)
    print(f"Developer Hint: {developer_guidance[:150]}...", flush=True)
    
    parser = parse_maven_failing if (test_cmd and test_cmd[0] == "mvn") else parse_pytest_failing
    env = RepoEnv(test_cmd=test_cmd, build_cmd=build_cmd,
                  target_test_cmd=target_test_cmd,
                  failing_test_parser=parser)
    
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
        disp = Dispatcher(workdir, log, bug_id, trigger_class=None, hint_file=None, env=env)
        disp.last_test = initial
        
        ctx = server_ctx()
        
        # Inject developer guidance into the initial history
        initial_history = [
            f"[system] Initial attempt previously escalated or reached turn limit.",
            f"[human developer guidance] {developer_guidance}",
            f"[system] Resume phase: TRY_FIX. Use the developer guidance to revise your hypothesis and apply an exact edit."
        ]
        
        outcome, escalation, attempts = run_fsm_core(
            disp, ctx, hint_file=None, log=log, bug_id=bug_id, env=env,
            extra_context=_issue_context(issue),
            initial_state="TRY_FIX",
            initial_history=initial_history,
            initial_attempts=0,
            max_turns=max_turns
        )
        
        summary = log.summary(bug_id, outcome, model=MODEL,
                              edits_applied=len(disp.edits),
                              fix_attempts=attempts, escalation=escalation)
        print(f"  -> {outcome} ({len(disp.edits)} edits)", flush=True)
        
        if outcome == "PLAUSIBLE":
            diff_text = env.diff(workdir)
            msg = _generate_commit_message(ctx, issue, diff_text)
            title = msg.splitlines()[0] if msg else f"Fix #{issue.number}"
            pr_body = (f"Closes #{issue.number}.\n\n{msg}\n\n"
                       f"_Opened automatically by repairlam after human-guided "
                       f"resumption ({attempts} edit attempt(s))._")
            if env.commit_and_push(workdir, branch, msg, COMMIT_AUTHOR_NAME, COMMIT_AUTHOR_EMAIL):
                pr = client.create_pull_request(repo_full_name, branch, base_branch, title, pr_body)
                return {"outcome": outcome, "pr_url": pr.html_url, "summary": summary}
                
        report = _escalation_report(issue, outcome, escalation, len(disp.edits))
        client.post_comment(repo_full_name, issue_number, f"[Interactive Resume Report]\n{report}")
        return {"outcome": outcome, "comment_posted": True, "summary": summary}
        
    finally:
        env.cleanup(workdir)
