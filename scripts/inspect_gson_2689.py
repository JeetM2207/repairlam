import os, requests

token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}

r = requests.get("https://api.github.com/repos/google/gson/issues/2689", headers=headers)
d = r.json()
print("2689 body:\n", d.get("body", "")[:1200])
