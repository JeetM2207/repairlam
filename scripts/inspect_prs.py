import os
import requests

token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3.diff"} if token else {"Accept": "application/vnd.github.v3.diff"}

for pr_num in [3006, 3059, 3000]:
    url = f"https://api.github.com/repos/google/gson/pulls/{pr_num}"
    r = requests.get(url, headers=headers)
    print(f"=== PR #{pr_num} DIFF ===")
    print(r.text[:2500])
    print("\n" + "="*40 + "\n")
