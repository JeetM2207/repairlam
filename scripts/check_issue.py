import os, requests

token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}
r = requests.get("https://api.github.com/repos/FasterXML/jackson-databind/issues/6185", headers=headers)
print("Status:", r.status_code)
if r.status_code == 200:
    data = r.json()
    print("Title:", data.get("title"))
    print("Body:\n", data.get("body")[:1000])
