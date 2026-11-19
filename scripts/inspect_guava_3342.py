import os, requests

token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}

r = requests.get("https://api.github.com/repos/google/guava/issues/3342/comments", headers=headers)
print("3342 comments:", len(r.json()))
for c in r.json():
    print(c["user"]["login"], ":", c["body"][:400])
