import os, requests

token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}

url = "https://api.github.com/search/issues?q=repo:FasterXML/jackson-databind+type:issue+state:open+in:title+fail+OR+error+OR+bug&sort=comments&order=desc&per_page=20"
r = requests.get(url, headers=headers)
print("Status:", r.status_code)
for item in r.json().get("items", []):
    print(f"#{item['number']}: {item['title']} ({item['comments']} comments)")
