"""Search GitHub repositories for candidate bug issues with reproducible test cases."""
import os
import sys
from github import Github

token = os.environ.get("GITHUB_TOKEN")
if not token:
    print("ERROR: GITHUB_TOKEN not set")
    sys.exit(1)

g = Github(token)

REPOS = [
    "google/gson",
    "google/guava",
    "FasterXML/jackson-databind",
    "FasterXML/jackson-core",
    "apache/commons-lang",
    "apache/commons-text",
]

def scan_repo(repo_name, max_candidates=5):
    print(f"\nScanning {repo_name}...", flush=True)
    repo = g.get_repo(repo_name)
    candidates = []
    
    issues = repo.get_issues(state="open")
    count = 0
    for issue in issues:
        if issue.pull_request:
            continue
        count += 1
        if count > 80:
            break
            
        labels = [l.name.lower() for l in issue.labels]
        has_bug_label = any("bug" in l or "defect" in l for l in labels)
        
        body = issue.body or ""
        has_test_code = ("```java" in body or "```" in body) and any(
            k in body for k in ["@Test", "assert", "assertEquals", "assertThat", "expected", "throws", "new "]
        )
        
        if has_test_code:
            candidates.append({
                "number": issue.number,
                "title": issue.title,
                "labels": labels,
                "has_bug_label": has_bug_label,
                "body_len": len(body),
                "url": issue.html_url
            })
            print(f"  [#{issue.number}] {issue.title} (bug_label={has_bug_label})", flush=True)
            if len(candidates) >= max_candidates:
                break
                
    return candidates

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    repos = [target] if target else REPOS
    for r in repos:
        try:
            scan_repo(r, max_candidates=4)
        except Exception as e:
            print(f"Error scanning {r}: {e}", flush=True)
