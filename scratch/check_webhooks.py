import os
import httpx
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENWA_API_KEY")
resp = httpx.get("http://localhost:2785/api/webhooks", headers={"X-API-Key": api_key})
import json
print(json.dumps(resp.json(), indent=2))
