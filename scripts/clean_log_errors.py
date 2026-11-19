import json

path = "/home/23ucs603/btp/repairlam/results/live_run_log.json"
data = json.load(open(path))
initial_count = len(data["runs"])
# Filter out the recent runs that failed with 401 Bad credentials
data["runs"] = [r for r in data["runs"] if not (r.get("outcome") == "ERROR" and "Bad credentials" in str(r.get("note", "")))]
print(f"Cleaned live_run_log.json: {initial_count} -> {len(data['runs'])} runs")
with open(path, "w") as f:
    json.dump(data, f, indent=2)
