import os, requests
from dotenv import load_dotenv

load_dotenv()
token = os.environ.get("GITHUB_TOKEN")
headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3.diff",
} if token else {}

def inspect_pr(repo, pr_num):
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_num}"
    r = requests.get(url, headers=headers)
    print(f"=== {repo} PR #{pr_num} ===")
    print(r.text[:2000])
    print("\n" + "="*40 + "\n")

inspect_pr("apache/commons-csv", 614)
inspect_pr("apache/commons-csv", 609)
inspect_pr("apache/commons-csv", 612)
inspect_pr("jhy/jsoup", 1843)
inspect_pr("jhy/jsoup", 2266)
