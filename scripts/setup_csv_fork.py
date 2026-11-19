import os
from github import Github, Auth
from dotenv import load_dotenv

load_dotenv()
token = os.environ.get("GITHUB_TOKEN")
gh = Github(auth=Auth.Token(token))
me = gh.get_user()
print("Authenticated as:", me.login)

# Ensure fork
upstream_name = "apache/commons-csv"
fork_name = f"{me.login}/commons-csv"
try:
    fork = gh.get_repo(fork_name)
    print(f"Fork {fork_name} already exists.")
except Exception:
    print(f"Creating fork {fork_name}...")
    upstream = gh.get_repo(upstream_name)
    fork = me.create_fork(upstream)
    print("Fork created!")

# Create branch bug-628 at base.sha
sha = "4b9e7de387e02c654d91bebf8bd021143a165809"
branch_name = "bug-628"
try:
    fork.get_branch(branch_name)
    print(f"Branch {branch_name} already exists.")
except Exception:
    print(f"Creating branch {branch_name} at {sha}...")
    fork.create_git_ref(ref=f"refs/heads/{branch_name}", sha=sha)
    print(f"Branch {branch_name} created!")
