# server.py
import logging

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from src.langgraph_whatsapp.channel import WhatsAppAgentOpenWA

from contextlib import asynccontextmanager

LOGGER = logging.getLogger("server")
WSP_AGENT = WhatsAppAgentOpenWA()

@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    LOGGER.info("Server starting up. Firing initial session restart to boot WAHA...")
    asyncio.create_task(WSP_AGENT.force_restart_session())
    asyncio.create_task(monitor_session_health())
    yield

APP = FastAPI(lifespan=lifespan)

from src.langgraph_whatsapp.config import OPENWA_API_URL, OPENWA_API_KEY, OPENWA_SESSION_ID
import httpx

async def monitor_session_health():
    import asyncio
    while True:
        try:
            await asyncio.sleep(60)
            LOGGER.info("Running periodic session health check...")
            async with httpx.AsyncClient() as client:
                headers = {"X-API-Key": OPENWA_API_KEY}
                url = f"{OPENWA_API_URL.rstrip('/')}/sessions/{OPENWA_SESSION_ID}"
                resp = await client.get(url, headers=headers, timeout=10.0)
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status", "").upper()
                    if status in ["DISCONNECTED", "STOPPED", "FAILED"]:
                        LOGGER.warning(f"Periodic monitor detected session is {status}! Restarting...")
                        await WSP_AGENT.force_restart_session()
        except Exception as e:
            LOGGER.error(f"Error in periodic session monitor: {e}")



@APP.post("/whatsapp")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        # OpenWA webhooks are JSON by default
        payload = await request.json()
        print("INCOMING WEBHOOK:", payload)
        
        # Proactively detect session crash
        if payload.get("event") == "session.status":
            session_status = payload.get("payload", {}).get("status", "").upper()
            if session_status in ["STOPPED", "FAILED", "DISCONNECTED"]:
                LOGGER.error(f"CRITICAL: WAHA Session crashed with status {session_status}! Auto-restarting...")
                import asyncio
                asyncio.create_task(WSP_AGENT.force_restart_session())
                return JSONResponse(content={"status": "ok"})
                
    except Exception as e:
        LOGGER.warning("Failed to parse JSON from webhook", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Acknowledge the webhook immediately with a 200 OK so OpenWA doesn't timeout,
    # and run the LangGraph processing in the background.
    background_tasks.add_task(WSP_AGENT.handle_message, payload)

    return JSONResponse(content={"status": "ok"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(APP, host="0.0.0.0", port=8081, log_level="info")

