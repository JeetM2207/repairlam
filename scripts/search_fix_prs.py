import os, requests
from dotenv import load_dotenv

load_dotenv()
token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}

def search_prs(repo):
    url = f"https://api.github.com/search/issues?q=repo:{repo}+type:pr+is:merged+fix&per_page=15"
    r = requests.get(url, headers=headers)
    items = r.json().get("items", [])
    print(f"=== PRs for {repo} ===")
    for item in items:
        print(f"#{item['number']}: {item['title']}")

search_prs("apache/commons-csv")
search_prs("jhy/jsoup")
