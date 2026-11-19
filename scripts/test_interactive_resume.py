import os
import sys
from dotenv import load_dotenv

load_dotenv("/home/23ucs603/btp/repairlam/.env", override=True)
sys.path.insert(0, "/home/23ucs603/btp/repairlam")

from repairlam.agent.interactive import resume_from_feedback
from repairlam.github.bug_specs import _csv_cmd

token = os.environ["GITHUB_TOKEN"]
developer_guidance = (
    "In CSVRecord.java, in method isMapped(final String name), check that name is not null before calling "
    "headerMap.containsKey(name), like: 'return headerMap != null && name != null && headerMap.containsKey(name);'. "
    "When ignoreHeaderCase is true, headerMap is a TreeMap with CaseInsensitiveComparator which crashes on null key."
)

test_cmd = _csv_cmd("CSVRecordTest#testIsMappedNullWithIgnoreHeaderCase")

result = resume_from_feedback(
    repo_full_name="JeetM2207/commons-csv",
    issue_number=4,
    token=token,
    developer_guidance=developer_guidance,
    test_cmd=test_cmd,
    base_branch="master",
    max_turns=15
)

print("\n=== RESUME RESULT ===")
print("Outcome:", result.get("outcome"))
print("PR URL:", result.get("pr_url"))
print("Summary:", result.get("summary"))
