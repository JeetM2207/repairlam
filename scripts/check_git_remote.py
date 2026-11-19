import os
import sys
sys.path.insert(0, "/home/23ucs603/btp/repairlam")
from repairlam.github.repo_env import git_auth_env, _run
from dotenv import load_dotenv

load_dotenv("/home/23ucs603/btp/repairlam/.env")
env = git_auth_env()
rc, out, err = _run(["git", "ls-remote", "https://github.com/JeetM2207/commons-csv.git", "HEAD"], extra_env=env)
print("ls-remote rc:", rc, "out:", out.strip())
