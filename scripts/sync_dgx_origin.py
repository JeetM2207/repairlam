import os
import sys
sys.path.insert(0, "/home/23ucs603/btp/repairlam")
from repairlam.github.repo_env import git_auth_env, _run
from dotenv import load_dotenv

load_dotenv("/home/23ucs603/btp/repairlam/.env", override=True)
env = git_auth_env()
rc, out, err = _run(["git", "fetch", "origin", "master"], cwd="/home/23ucs603/btp/repairlam", extra_env=env)
print("Fetch rc:", rc, out.strip(), err.strip())
rc, out, err = _run(["git", "reset", "--hard", "origin/master"], cwd="/home/23ucs603/btp/repairlam")
print("Reset rc:", rc, out.strip())
rc, out, err = _run(["git", "log", "-n", "1", "--oneline"], cwd="/home/23ucs603/btp/repairlam")
print("Head:", out.strip())
