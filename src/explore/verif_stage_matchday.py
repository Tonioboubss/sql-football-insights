
"""Inspect how 'stage' and 'matchday' actually co-occur across match
types, before writing the load logic that maps them."""

import json
from pathlib import Path

data = json.loads(Path("data/raw/CL_matches.json").read_text())
matches = data["matches"]

seen_stages = set()
for m in matches:
    if m["stage"] not in seen_stages:
        seen_stages.add(m["stage"])
        print(m["stage"], "-> matchday:", m["matchday"], "| date:", m["utcDate"])