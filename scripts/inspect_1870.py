import os, requests

token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}

r = requests.get("https://api.github.com/repos/google/gson/issues/1870", headers=headers)
print("1870 status:", r.status_code)
d = r.json()
print("Title:", d.get("title"))
print("Body:\n", d.get("body")[:1500])
