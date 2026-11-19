import os
from github import Github

token = os.environ.get("GITHUB_TOKEN")
g = Github(token)

repo = g.get_repo("google/gson")
pr = repo.get_pull(3059)
print(f"=== PR #{pr.number}: {pr.title} ===")
print("Body:", pr.body)
for f in pr.get_files():
    print(f"\n--- {f.filename} ---")
    print(f.patch)
