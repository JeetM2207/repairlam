import os, requests
from dotenv import load_dotenv

load_dotenv()
token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}

def search_open(repo):
    url = f"https://api.github.com/search/issues?q=repo:{repo}+is:open+is:issue+label:bug&sort=comments&order=desc&per_page=15"
    r = requests.get(url, headers=headers)
    items = r.json().get("items", [])
    print(f"=== OPEN BUGS in {repo} ===")
    for item in items:
        print(f"#{item['number']}: {item['title']} (comments={item['comments']})")

search_open("google/gson")
search_open("google/guava")
search_open("FasterXML/jackson-databind")
