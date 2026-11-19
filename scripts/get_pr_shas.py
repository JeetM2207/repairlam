import os, requests
from dotenv import load_dotenv

load_dotenv()
token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}

def get_pr_base_sha(repo, pr_num):
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_num}"
    r = requests.get(url, headers=headers)
    d = r.json()
    base_sha = d.get("base", {}).get("sha")
    title = d.get("title")
    merge_commit = d.get("merge_commit_sha")
    print(f"{repo} PR #{pr_num}: {title}")
    print(f"  base.sha: {base_sha}")
    print(f"  merge_commit: {merge_commit}")
    return base_sha

print("=== Commons-CSV ===")
get_pr_base_sha("apache/commons-csv", 610)
get_pr_base_sha("apache/commons-csv", 628)
get_pr_base_sha("apache/commons-csv", 614)
get_pr_base_sha("apache/commons-csv", 609)
get_pr_base_sha("apache/commons-csv", 612)

print("\n=== JSoup ===")
get_pr_base_sha("jhy/jsoup", 2620)
get_pr_base_sha("jhy/jsoup", 2596)
get_pr_base_sha("jhy/jsoup", 2610)
