import os
import requests

token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}

url = "https://api.github.com/search/issues?q=repo:google/guava+type:issue+state:open+label:type=defect&sort=comments&order=desc&per_page=30"
r = requests.get(url, headers=headers)
print("Status:", r.status_code)
if r.status_code == 200:
    for item in r.json().get("items", []):
        print(f"#{item['number']}: {item['title']} ({item['comments']} comments)")
else:
    # try without label
    url2 = "https://api.github.com/search/issues?q=repo:google/guava+type:issue+state:open+bug+in:title&sort=comments&order=desc&per_page=30"
    r2 = requests.get(url2, headers=headers)
    print("Status2:", r2.status_code)
    for item in r2.json().get("items", []):
        print(f"#{item['number']}: {item['title']} ({item['comments']} comments)")
