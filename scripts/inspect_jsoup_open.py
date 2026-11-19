import os, requests
from dotenv import load_dotenv

load_dotenv()
token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}

def get_issue(repo, num):
    r = requests.get(f"https://api.github.com/repos/{repo}/issues/{num}", headers=headers)
    d = r.json()
    print(f"=== {repo} #{num}: {d.get('title')} ({d.get('state')}) ===")
    print((d.get('body') or '')[:1500])
    print("\n" + "="*50 + "\n")

get_issue("jhy/jsoup", 2266)
get_issue("jhy/jsoup", 2476)
get_issue("jhy/jsoup", 2475)
get_issue("jhy/jsoup", 1843)
get_issue("jhy/jsoup", 1877)
