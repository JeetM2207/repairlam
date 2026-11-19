import os, requests
from dotenv import load_dotenv

load_dotenv()
token = os.environ.get("GITHUB_TOKEN")
headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json",
} if token else {}

def find_closing_pr(repo, issue_num):
    url = f"https://api.github.com/repos/{repo}/issues/{issue_num}/timeline"
    headers_tl = {**headers, "Accept": "application/vnd.github.mockingbird-preview+json"}
    r = requests.get(url, headers=headers_tl)
    for event in r.json():
        if event.get("event") == "cross-referenced":
            source = event.get("source", {}).get("issue", {})
            if "pull_request" in source:
                print(f"Issue #{issue_num} closed by PR #{source['number']}: {source['title']}")
                return source['number']
    print(f"No cross-referenced PR found for issue #{issue_num}")
    return None

find_closing_pr("jhy/jsoup", 1843)
find_closing_pr("jhy/jsoup", 2266)
find_closing_pr("jhy/jsoup", 1877)
find_closing_pr("jhy/jsoup", 2476)
