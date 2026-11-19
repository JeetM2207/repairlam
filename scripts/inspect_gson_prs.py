import os, requests

token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3.diff"} if token else {"Accept": "application/vnd.github.v3.diff"}

for pr in [3034, 3096]:
    r = requests.get(f"https://api.github.com/repos/google/gson/pulls/{pr}", headers=headers)
    print(f"=== PR {pr} DIFF ===")
    print(r.text[:2000])
    print("\n" + "="*40 + "\n")
