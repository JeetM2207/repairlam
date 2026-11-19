import os, requests
from dotenv import load_dotenv

load_dotenv()
token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"}

r = requests.get("https://api.github.com/user/repos?type=owner&per_page=100", headers=headers)
print("Repositories owned by JeetM2207:")
for repo in r.json():
    print(f"- {repo['full_name']} (fork of {repo.get('parent', {}).get('full_name', 'N/A') if repo.get('fork') else 'own'})")
