import os, requests
from dotenv import load_dotenv

load_dotenv()
token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"} if token else {}

for num in [3047, 3128, 3122]:
    r = requests.get(f"https://api.github.com/repos/google/gson/issues/{num}", headers=headers)
    d = r.json()
    print(f"=== GSON #{num}: {d.get('title')} ===")
    print(d.get("body", "")[:1500])
    print("\n" + "="*50 + "\n")
