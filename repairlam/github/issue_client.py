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
        from github import Github, Auth  # PyGithub
        self._gh = Github(auth=Auth.Token(token))

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

    def create_issue(self, repo_full_name, title, body) -> Issue:
        repo = self.get_repo(repo_full_name)
        issue = repo.create_issue(title=title, body=body)
        return Issue(number=issue.number, title=issue.title or "",
                    body=issue.body or "", url=issue.html_url)

    def ensure_fork(self, source_repo_full_name):
        """Idempotent: returns the full_name of the authenticated user's
        fork of `source_repo_full_name`, creating it first if it doesn't
        already exist."""
        me = self._gh.get_user()
        owner, name = source_repo_full_name.split("/")
        target = f"{me.login}/{name}"
        try:
            self._gh.get_repo(target)
            return target
        except Exception:
            pass
        src = self.get_repo(source_repo_full_name)
        me.create_fork(src)
        import time
        for _ in range(30):
            try:
                self._gh.get_repo(target)
                return target
            except Exception:
                time.sleep(2)
        raise RuntimeError(f"fork of {source_repo_full_name} did not "
                           f"become available in time")

    def ensure_issues_enabled(self, repo_full_name):
        repo = self.get_repo(repo_full_name)
        if not repo.has_issues:
            repo.edit(has_issues=True)

    def create_pull_request(self, repo_full_name, head_branch, base_branch,
                            title, body):
        repo = self.get_repo(repo_full_name)
        return repo.create_pull(title=title, body=body, head=head_branch,
                                base=base_branch)

    def clone_url(self, repo_full_name):
        """Plain https clone URL, no credential embedded. Authentication
        for git clone/push happens separately via GIT_ASKPASS (see
        repairlam.github.repo_env.git_auth_env) reading $GITHUB_TOKEN from
        the environment at call time -- never via a URL, so it can't leak
        through git's own error/diagnostic output the way an
        embedded-token URL can."""
        return self.get_repo(repo_full_name).clone_url
