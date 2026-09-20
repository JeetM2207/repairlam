"""Integration test for Module 4 (repairlam/github): runs the real FSM
against a tiny seeded-bug Java/Maven repo (tests/fixtures/seed_repo) through
the actual pipeline.run_on_issue(), with a fake GithubClient standing in
for the real GitHub API -- so it exercises everything (clone, FSM, commit,
push, PR-vs-comment branching, commit message generation) except the
final network call to github.com.

Needs: the vLLM server reachable at BASE_URL, network access (Maven
downloads plugins/deps on first run), and `mvn` on PATH. Skipped
automatically if the server isn't reachable, since this repo's CI/dev
environment isn't guaranteed to have it running -- this is a slow,
model-driven integration test, not a fast unit test.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from repairlam.github import pipeline
from repairlam.github.issue_client import Issue
from repairlam.github.repo_env import parse_maven_failing, maven_target_test_cmd

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "seed_repo"
BASE_URL = "http://localhost:8603/v1"


def _server_up():
    try:
        return requests.get(f"{BASE_URL}/models", timeout=3).status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _server_up(),
                                reason="vLLM server not reachable; this is "
                                       "a model-driven integration test")


class FakePR:
    html_url = "https://example.invalid/pull/1"


class FakeGithubClient:
    def __init__(self, title, body):
        self.title, self.body = title, body
        self.posted_comments = []
        self.created_prs = []

    def get_issue(self, repo_full_name, issue_number):
        return Issue(number=issue_number, title=self.title, body=self.body,
                    url="https://example.invalid/issues/1")

    def post_comment(self, repo_full_name, issue_number, body):
        self.posted_comments.append(body)

    def create_pull_request(self, repo_full_name, head_branch, base_branch, title, body):
        self.created_prs.append({"title": title, "body": body,
                                 "head": head_branch, "base": base_branch})
        return FakePR()

    def clone_url(self, repo_full_name):
        return str(self._seed_path)


@pytest.fixture
def seeded_repo(tmp_path):
    """A fresh git repo (with the intentional factorial off-by-one bug)
    under tmp_path, on branch 'main', ready to be cloned by RepoEnv."""
    repo = tmp_path / "seed"
    shutil.copytree(FIXTURE, repo)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@test.com",
                    "commit", "-q", "-m", "seed: buggy MathUtils.factorial"],
                   cwd=repo, check=True)
    subprocess.run(["git", "branch", "-M", "main"], cwd=repo, check=True)
    return repo


def test_plausible_fix_opens_pr(seeded_repo):
    client = FakeGithubClient(
        title="factorial(5) returns the wrong value",
        body=("MathUtils.factorial(5) should return 120 but returns 24. "
              "factorial(0) and factorial(1) work fine."))
    client._seed_path = seeded_repo

    result = pipeline.run_on_issue(
        repo_full_name="fake-org/seed-repo", issue_number=1, token=None,
        client=client, test_cmd=["mvn", "-q", "test"], build_cmd=None,
        target_test_cmd=maven_target_test_cmd, base_branch="main",
        dry_run=False)

    assert result["outcome"] == "PLAUSIBLE"
    assert len(client.created_prs) == 1
    assert len(client.posted_comments) == 0
    pr = client.created_prs[0]
    assert "1" in pr["body"]  # references the issue

    # the actual fix must have been committed for real
    log = subprocess.run(["git", "log", "repairlam/issue-1", "-1", "-p"],
                         cwd=seeded_repo, capture_output=True, text=True, check=True)
    assert "i <= n" in log.stdout
