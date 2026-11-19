import os, requests

token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}

r = requests.get("https://api.github.com/repos/google/gson/issues/2816", headers=headers)
d = r.json()
print("2816 body:\n", d.get("body", "")[:1200])

r_c = requests.get("https://api.github.com/repos/google/gson/issues/2816/comments", headers=headers)
for c in r_c.json():
    print(c["user"]["login"], ":", c["body"][:300])
