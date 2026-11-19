import os
import requests

token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}

def search_prs(repo):
    url = f"https://api.github.com/search/issues?q=repo:{repo}+type:pr+is:merged+Fix+in:title&sort=created&order=desc&per_page=20"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print(f"Error {r.status_code}")
        return []
    items = r.json().get("items", [])
    results = []
    for item in items:
        results.append({
            "number": item["number"],
            "title": item["title"],
            "url": item["pull_request"]["url"]
        })
    return results

print("=== GSON MERGED FIX PRS ===")
for pr in search_prs("google/gson")[:15]:
    print(f"PR #{pr['number']}: {pr['title']}")

print("\n=== GUAVA MERGED FIX PRS ===")
for pr in search_prs("google/guava")[:15]:
    print(f"PR #{pr['number']}: {pr['title']}")
