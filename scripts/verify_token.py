import os
from dotenv import load_dotenv
from github import Github, Auth

load_dotenv("/home/23ucs603/btp/repairlam/.env", override=True)
token = os.environ.get("GITHUB_TOKEN")
print("Token prefix:", token[:10] if token else "None")
gh = Github(auth=Auth.Token(token))
me = gh.get_user()
print("Authenticated user:", me.login)
repo = gh.get_repo("JeetM2207/commons-csv")
print("Repo full_name:", repo.full_name)
print("Success!")
