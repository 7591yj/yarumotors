import fastf1
import json
from pathlib import Path

data = {}

base = Path(__file__).resolve().parent
target = base.parent.parent / "bot" / "src" / "utils" / "gps.json"

for year in range(2019, 2026):
    schedule = fastf1.get_event_schedule(year)
    data[year] = schedule["Country"].tolist()

with target.open("w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
