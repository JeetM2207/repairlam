import os
import sys
from github import Github

token = os.environ.get("GITHUB_TOKEN")
g = Github(token)

repos = ["google/gson", "FasterXML/jackson-databind", "google/guava"]

for r_name in repos:
    print(f"\n--- Merged bugfix PRs in {r_name} ---")
    r = g.get_repo(r_name)
    pulls = r.get_pulls(state="closed", sort="updated", direction="desc")
    count = 0
    for p in pulls:
        if not p.merged:
            continue
        count += 1
        if count > 40:
            break
        title_lower = p.title.lower()
        if any(w in title_lower for w in ["fix", "bug", "issue #", "resolves", "closes"]):
            # Check if has test files
            files = list(p.get_files())
            test_files = [f for f in files if "test" in f.filename.lower() and f.filename.endswith(".java")]
            src_files = [f for f in files if "test" not in f.filename.lower() and f.filename.endswith(".java")]
            if test_files and src_files and len(src_files) <= 3:
                print(f"  [PR #{p.number}] {p.title} (tests={len(test_files)}, src={len(src_files)})")
                print(f"    Base: {p.base.ref} | Merged: {p.merged_at}")
                for f in src_files:
                    print(f"      Src: {f.filename} (+{f.additions} -{f.deletions})")
                for f in test_files:
                    print(f"      Test: {f.filename}")
