import sys
sys.path.insert(0, "/home/23ucs603/btp/repairlam")

import repairlam.agent.loop
import repairlam.agent.interactive
import repairlam.github.live_bug_pipeline
from repairlam.github.bug_specs import SPECS

print("Pipeline imports succeeded.")
print("Total SPECS count:", len(SPECS))
print("Newest specs:", [s.key for s in SPECS[-3:]])
