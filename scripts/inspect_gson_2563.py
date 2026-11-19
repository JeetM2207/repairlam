import os, requests

token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}

r = requests.get("https://api.github.com/repos/google/gson/issues/2563", headers=headers)
d = r.json()
print("2563 title:", d.get("title"))
print("2563 body:\n", d.get("body", "")[:1200])
