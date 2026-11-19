import os
import sys
from github import Github

token = os.environ.get("GITHUB_TOKEN")
g = Github(token)

repo_name = sys.argv[1] if len(sys.argv) > 1 else "google/gson"
num = int(sys.argv[2]) if len(sys.argv) > 2 else 3122

repo = g.get_repo(repo_name)
issue = repo.get_issue(num)
print(f"=== Issue #{num}: {issue.title} ===")
print(issue.body)
print("\n--- COMMENTS ---")
for c in issue.get_comments():
    print(f"[{c.user.login}]: {c.body[:300]}...\n")
