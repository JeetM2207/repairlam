import os
import requests
from dotenv import load_dotenv

load_dotenv()
token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

payload = {
    "name": "repairlam",
    "description": "RepairLAM: Action-Constrained Large Action Model Framework for Autonomous Software Maintenance",
    "private": False,
    "has_issues": True,
    "has_projects": True,
    "has_wiki": False
}

r = requests.post("https://api.github.com/user/repos", headers=headers, json=payload)
print("Create repo status:", r.status_code)
if r.status_code in [201, 422]:  # 422 means already exists
    print("Repo URL:", r.json().get("html_url", "https://github.com/JeetM2207/repairlam"))
    print("Clone URL:", r.json().get("clone_url", "https://github.com/JeetM2207/repairlam.git"))
else:
    print("Error:", r.text)
