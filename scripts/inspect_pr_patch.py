import os
import sys
from github import Github

token = os.environ.get("GITHUB_TOKEN")
g = Github(token)

repo = g.get_repo("FasterXML/jackson-databind")
pr = repo.get_pull(6202)
for f in pr.get_files():
    if "Test" in f.filename:
        print(f"=== {f.filename} ===")
        print(f.patch)
