import os, requests

token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3.diff"} if token else {"Accept": "application/vnd.github.v3.diff"}

r = requests.get("https://api.github.com/repos/google/gson/pulls/1023", headers=headers)
print("PR 1023 status:", r.status_code)
print(r.text[:2000])
