import os
import requests

token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}

url = "https://api.github.com/search/issues?q=repo:google/gson+type:issue+state:open+label:bug&sort=comments&order=desc&per_page=30"
r = requests.get(url, headers=headers)
print("Status:", r.status_code)
if r.status_code == 200:
    for item in r.json().get("items", []):
        print(f"#{item['number']}: {item['title']} ({item['comments']} comments)")
