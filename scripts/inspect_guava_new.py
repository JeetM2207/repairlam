import os, requests

token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}

for num in [8693, 3342]:
    r = requests.get(f"https://api.github.com/repos/google/guava/issues/{num}", headers=headers)
    if r.status_code == 200:
        d = r.json()
        print(f"=== GUAVA #{num}: {d['title']} ===")
        print(d.get("body", "")[:1200])
        print("\n" + "="*40 + "\n")
