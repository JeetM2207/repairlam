import os
from dotenv import load_dotenv
from github import Github, Auth

load_dotenv()
token = os.environ.get("GITHUB_TOKEN")
gh = Github(auth=Auth.Token(token))
me = gh.get_user()
repo = gh.get_repo("JeetM2207/commons-csv")

# Ensure issues enabled
if not repo.has_issues:
    repo.edit(has_issues=True)
    print("Enabled issues on JeetM2207/commons-csv")
else:
    print("Issues already enabled on JeetM2207/commons-csv")

# List open issues
open_issues = list(repo.get_issues(state="open"))
print(f"Open issues on JeetM2207/commons-csv: {len(open_issues)}")
for iss in open_issues:
    print(f"  #{iss.number}: {iss.title}")

if not open_issues:
    # Create issue for CSV custom comment quote
    issue = repo.create_issue(
        title="Quote value starting with comment marker in minimal quote mode",
        body="""When a custom comment marker is set in CSVFormat (e.g. ';'), printing a value that starts with that comment marker in minimal quote mode outputs it unquoted (e.g. ';comment-like').
When the CSV is parsed back, the parser treats ';comment-like' as a comment line and ignores it, causing data loss.
Values starting with the configured comment marker must be enclosed in quotes so they round-trip accurately through the parser."""
    )
    print(f"Created issue #{issue.number}: {issue.html_url}")
