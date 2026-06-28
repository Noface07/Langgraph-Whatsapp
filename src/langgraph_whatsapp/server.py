# server.py
import logging

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from src.langgraph_whatsapp.channel import WhatsAppAgentOpenWA

LOGGER = logging.getLogger("server")
APP = FastAPI()
WSP_AGENT = WhatsAppAgentOpenWA()


@APP.post("/whatsapp")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        # OpenWA webhooks are JSON by default
        payload = await request.json()
        print("INCOMING WEBHOOK:", payload)
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

