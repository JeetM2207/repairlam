import os, requests

token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}

r = requests.get("https://api.github.com/repos/google/gson/issues/1768/comments", headers=headers)
print("1768 comments:", len(r.json()))
for c in r.json():
    print(c["user"]["login"], ":", c["body"][:300])

r2 = requests.get("https://api.github.com/repos/google/gson/issues/2393/comments", headers=headers)
print("2393 comments:", len(r2.json()))
for c in r2.json():
    print(c["user"]["login"], ":", c["body"][:300])
