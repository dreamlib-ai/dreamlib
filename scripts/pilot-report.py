"""Read Railway JSONL product_event logs from stdin. Never prints identities or content."""
import json
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
events = defaultdict(set)
actors = defaultdict(set)
days = defaultdict(set)
for line in sys.stdin:
    try:
        row = json.loads(line)
        message = row.get("message", "")
        if "product_event " not in message:
            continue
        event = json.loads(message.split("product_event ", 1)[1])
        name, actor, eid = event["name"], event["actor"], event["eventId"]
        events[name].add((actor, eid))
        actors[name].add(actor)
        date = row.get("timestamp", "")[:10]
        if name == "session_open" and date:
            days[actor].add(date)
    except (ValueError, KeyError, TypeError):
        continue
for name in ["session_open", "record_started", "transcript_ready", "analysis_ready", "booklet_ready", "dream_saved", "feedback_helpful", "feedback_unhelpful"]:
    print(f"{name}: {len(events[name])} unique events, {len(actors[name])} accounts")
print("Accounts seen on multiple days:", sum(len(d) > 1 for d in days.values()))
print("Counts cover only the supplied log window; this is not a complete retention report.")
