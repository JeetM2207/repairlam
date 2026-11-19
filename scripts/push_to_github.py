import os
import subprocess
from dotenv import load_dotenv

load_dotenv()
token = os.environ.get("GITHUB_TOKEN")

# Setup remote if not already present
remotes = subprocess.run(["git", "remote"], capture_output=True, text=True).stdout.split()
if "origin" in remotes:
    subprocess.run(["git", "remote", "set-url", "origin", "https://github.com/JeetM2207/repairlam.git"])
else:
    subprocess.run(["git", "remote", "add", "origin", "https://github.com/JeetM2207/repairlam.git"])

print("Remote configured:")
subprocess.run(["git", "remote", "-v"])

# Push to origin master using authenticated URL for push only or askpass
auth_url = f"https://x-access-token:{token}@github.com/JeetM2207/repairlam.git"
p = subprocess.run(["git", "push", "-u", auth_url, "master"], capture_output=True, text=True)
print("Push returncode:", p.returncode)
print("Push stdout:", p.stdout)
print("Push stderr:", p.stderr.replace(token, "***"))

# Ensure remote URL stored in config remains clean without token
subprocess.run(["git", "remote", "set-url", "origin", "https://github.com/JeetM2207/repairlam.git"])
print("Origin set to clean URL.")
