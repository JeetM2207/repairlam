import os, requests

token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}

r = requests.get("https://api.github.com/repos/google/gson/issues/1870/comments", headers=headers)
print("1870 comments:", len(r.json()))
for c in r.json():
    print(c["user"]["login"], ":", c["body"][:400])
