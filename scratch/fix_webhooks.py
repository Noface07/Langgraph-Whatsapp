import os
import httpx
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENWA_API_KEY")

headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
get_resp = httpx.get("http://localhost:2785/api/webhooks", headers=headers)
webhooks = get_resp.json()

for wh in webhooks:
    wh_id = wh["id"]
    sess_id = wh["sessionId"]
    
    events = wh.get("events", [])
    if "message.received" not in events:
        events.append("message.received")
    if "message.sent" not in events:
        events.append("message.sent")
        
    payload = {
        "url": wh["url"],
        "events": events,
    }
    put_resp = httpx.put(f"http://localhost:2785/api/sessions/{sess_id}/webhooks/{wh_id}", headers=headers, json=payload)
    print(f"Updated webhook {wh_id}: {put_resp.status_code}")
