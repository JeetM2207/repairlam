import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
token = os.environ.get("GITHUB_TOKEN")
headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json",
} if token else {}

def search_repo_issues(repo, query="is:closed is:issue label:bug"):
    url = f"https://api.github.com/search/issues?q=repo:{repo}+{query}&sort=comments&order=asc&per_page=15"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print(f"Error {r.status_code}: {r.text[:200]}")
        return []
    items = r.json().get("items", [])
    results = []
    for item in items:
        results.append({
            "number": item["number"],
            "title": item["title"],
            "html_url": item["html_url"],
            "body": (item.get("body") or "")[:300]
        })
    return results

print("Searching jhy/jsoup...")
jsoup_issues = search_repo_issues("jhy/jsoup")
for iss in jsoup_issues:
    print(f"jsoup#{iss['number']}: {iss['title']}")

print("\nSearching apache/commons-csv...")
csv_issues = search_repo_issues("apache/commons-csv", "is:closed is:issue")
for iss in csv_issues:
    print(f"commons-csv#{iss['number']}: {iss['title']}")
