import json

d = json.load(open("/home/23ucs603/btp/repairlam/results/live_run_log.json"))
print("Runs count:", len(d["runs"]))
print("Last 3 runs:")
for r in d["runs"][-3:]:
    print(" ", r["key"], "->", r.get("outcome"), "PR:", r.get("pr_url"))
