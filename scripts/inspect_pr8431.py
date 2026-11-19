import os, requests

token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3.diff"} if token else {"Accept": "application/vnd.github.v3.diff"}

r = requests.get("https://api.github.com/repos/google/guava/pulls/8431", headers=headers)
print("PR 8431 status:", r.status_code)
print(r.text[:2500])
