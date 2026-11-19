import os, requests

token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}

for num in [754, 576, 1011]:
    r = requests.get(f"https://api.github.com/repos/google/gson/issues/{num}", headers=headers)
    d = r.json()
    print(f"=== GSON #{num}: {d['title']} ===")
    print(d.get("body", "")[:1200])
    print("\n" + "="*40 + "\n")
