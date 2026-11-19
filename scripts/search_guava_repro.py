import os, requests

token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}

url = "https://api.github.com/search/issues?q=repo:google/guava+type:issue+state:open+label:type=defect+reproduce&sort=updated&order=desc&per_page=20"
r = requests.get(url, headers=headers)
print("Status:", r.status_code)
for item in r.json().get("items", []):
    print(f"#{item['number']}: {item['title']}")
