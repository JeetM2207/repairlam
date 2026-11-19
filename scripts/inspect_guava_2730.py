import os, requests

token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}

r = requests.get("https://api.github.com/repos/google/guava/issues/2730", headers=headers)
d = r.json()
print("Body 1200..3000:\n", d.get("body", "")[1200:3000])
