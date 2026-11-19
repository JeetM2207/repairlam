import os
import requests
from dotenv import load_dotenv

load_dotenv()
token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

payload = {
    "title": "CSVRecord.isMapped(null) throws NullPointerException when ignoreHeaderCase is true",
    "body": """Calling `CSVRecord.isMapped(null)` or `CSVRecord.isSet(null)` throws `NullPointerException` when `ignoreHeaderCase` is enabled.

When `ignoreHeaderCase` is enabled, the header map is initialized as a TreeMap with `String.CASE_INSENSITIVE_ORDER` comparator. In Java TreeMap, `containsKey(null)` invokes the comparator, causing a `NullPointerException`:
```java
java.lang.NullPointerException: Cannot read field "value" because "s1" is null
    at java.base/java.lang.String$CaseInsensitiveComparator.compare(String.java:2066)
    at java.base/java.util.TreeMap.containsKey(TreeMap.java:244)
    at org.apache.commons.csv.CSVRecord.isMapped(CSVRecord.java:246)
```

Expected behavior:
`record.isMapped(null)` and `record.isSet(null)` should safely return `false` without throwing `NullPointerException`."""
}

r = requests.post("https://api.github.com/repos/JeetM2207/commons-csv/issues", headers=headers, json=payload)
print("Status:", r.status_code)
print("Issue URL:", r.json().get("html_url"))
print("Issue Number:", r.json().get("number"))
