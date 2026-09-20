"""Thin PyGithub wrapper: read an issue, post a comment, open a pull
request. Nothing here is Defects4j-specific or FSM-specific -- it's pure
GitHub API glue, kept separate so it can be unit-tested with a fake/mock
client without touching the network or the FSM.
"""
from dataclasses import dataclass


@dataclass
class Issue:
    number: int
    title: str
    body: str
    url: str


class GithubClient:
    """Wraps PyGithub. Constructed with a personal access token; never logs
    or prints it. Import of `github` (PyGithub) is deferred into __init__
    so this module can be imported (e.g. for tests with a fake client)
    without the dependency installed."""

    def __init__(self, token):
        from github import Github  # PyGithub
        self._gh = Github(token)
        self._token = token

    def get_repo(self, repo_full_name):
        return self._gh.get_repo(repo_full_name)

    def get_issue(self, repo_full_name, issue_number) -> Issue:
        repo = self.get_repo(repo_full_name)
        issue = repo.get_issue(issue_number)
        return Issue(number=issue.number, title=issue.title or "",
                    body=issue.body or "", url=issue.html_url)

    def post_comment(self, repo_full_name, issue_number, body: str):
        repo = self.get_repo(repo_full_name)
        issue = repo.get_issue(issue_number)
        return issue.create_comment(body)

    def create_pull_request(self, repo_full_name, head_branch, base_branch,
                            title, body):
        repo = self.get_repo(repo_full_name)
        return repo.create_pull(title=title, body=body, head=head_branch,
                                base=base_branch)

    def authenticated_clone_url(self, repo_full_name):
        """https URL with the token embedded, for `git clone`/`git push`
        without an interactive credential prompt. Never print this --
        it contains the token."""
        repo = self.get_repo(repo_full_name)
        url = repo.clone_url  # "https://github.com/owner/name.git"
        return url.replace("https://", f"https://x-access-token:{self._token}@")
