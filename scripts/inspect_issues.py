import os
import requests

token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}

def inspect_issue(repo, num):
    r = requests.get(f"https://api.github.com/repos/{repo}/issues/{num}", headers=headers)
    if r.status_code == 200:
        d = r.json()
        print(f"=== {repo}#{num}: {d['title']} ===")
        print(d.get("body", "")[:1200])
        print("\n" + "-"*40 + "\n")

inspect_issue("google/guava", 1855)
inspect_issue("google/guava", 8426)
inspect_issue("google/guava", 345)
inspect_issue("google/gson", 1768)
inspect_issue("google/gson", 992)
