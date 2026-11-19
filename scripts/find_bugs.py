import os
import requests

token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}

def search_repo_issues(repo, query):
    url = f"https://api.github.com/search/issues?q=repo:{repo}+type:issue+state:closed+label:bug+{query}&sort=updated&order=desc&per_page=20"
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
            "comments": item["comments"]
        })
    return results

print("=== GSON ISSUES ===")
for iss in search_repo_issues("google/gson", "is:closed")[:10]:
    print(f"#{iss['number']}: {iss['title']}")

print("\n=== GUAVA ISSUES ===")
for iss in search_repo_issues("google/guava", "is:closed")[:10]:
    print(f"#{iss['number']}: {iss['title']}")
