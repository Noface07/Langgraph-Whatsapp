# channel.py
import logging
import httpx
from abc import ABC, abstractmethod

from fastapi import Request, HTTPException

from src.langgraph_whatsapp.agent import Agent
from src.langgraph_whatsapp.config import OPENWA_API_URL, OPENWA_API_KEY, OPENWA_SESSION_ID

LOGGER = logging.getLogger("whatsapp")

class WhatsAppAgent(ABC):
    @abstractmethod
    async def handle_message(self, request: Request) -> str: ...

class WhatsAppAgentOpenWA(WhatsAppAgent):
    def __init__(self) -> None:
        if not OPENWA_API_KEY:
            LOGGER.warning("OpenWA API key is missing. Ensure OPENWA_API_KEY is set in .env.")
        self.agent = Agent()

    async def _send_text(self, chat_id: str, text: str):
        send_url = f"{OPENWA_API_URL.rstrip('/')}/sessions/{OPENWA_SESSION_ID}/messages/send-text"
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": OPENWA_API_KEY
        }
        send_payload = {
            "chatId": chat_id,
            "text": text
        }
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(send_url, json=send_payload, headers=headers, timeout=30.0)
                if resp.status_code >= 400:
                    LOGGER.error(f"Failed to send OpenWA message: {resp.status_code} {resp.text}")
                    await self._restart_session_and_retry(client, headers, send_url, send_payload, chat_id)
                else:
                    LOGGER.info(f"Successfully sent reply to {chat_id}")
            except httpx.RequestError as e:
                LOGGER.error(f"Request Error while sending message: {e}")
                await self._restart_session_and_retry(client, headers, send_url, send_payload, chat_id)

    async def _restart_session_and_retry(self, client, headers, send_url, send_payload, chat_id):
        LOGGER.info("Attempting to restart the OpenWA session as a fallback...")
        start_url = f"{OPENWA_API_URL.rstrip('/')}/sessions/start"
        start_payload = {"name": OPENWA_SESSION_ID}
        try:
            start_resp = await client.post(start_url, json=start_payload, headers=headers, timeout=30.0)
            if start_resp.status_code in [200, 201]:
                LOGGER.info("Session restarted successfully. Retrying message send...")
                retry_resp = await client.post(send_url, json=send_payload, headers=headers, timeout=30.0)
                if retry_resp.status_code >= 400:
                    LOGGER.error(f"Failed to send OpenWA message after session restart: {retry_resp.status_code} {retry_resp.text}")
                else:
                    LOGGER.info(f"Successfully sent reply to {chat_id} after session restart")
            else:
                LOGGER.error(f"Failed to restart session: {start_resp.status_code} {start_resp.text}")
        except Exception as e:
            LOGGER.error(f"Error during session restart fallback: {e}")

    async def handle_message(self, payload: dict) -> str:

        # OpenWA webhook payload structure may vary slightly, but generally 
        # includes an 'event' and 'payload' with 'from' and 'body'.
        event_type = payload.get("event")
        if event_type not in ["message.received", "message.sent"]:
            LOGGER.info(f"Ignoring event type: {event_type}")
            return "ok"

        msg_data = payload.get("data", {})
        sender = msg_data.get("from", "").strip()
        content = msg_data.get("body", "").strip()

        # Handle self-messages for Remote Control (ON/OFF/LOG)
        is_from_me = msg_data.get("fromMe", False)
        is_group = msg_data.get("isGroup", False)
        id_field = msg_data.get("id")
        if isinstance(id_field, dict):
            is_from_me = is_from_me or id_field.get("fromMe", False)
            
        if is_from_me:
            import os
            text = content.strip().upper()
            
            # If the user texts "AI_ON", "AI_OFF", "AI_LOG", or "AI_DEL"
            if text in ["AI_ON", "AI_OFF"]:
                state_val = "on" if text == "AI_ON" else "off"
                with open(".bot_state", "w") as f:
                    f.write(state_val)
                # We can reply to the same chat we sent it in
                reply_to = msg_data.get("to") or sender
                await self._send_text(reply_to, f"Bot turned {state_val.upper()}")
                return "ok"
            elif text == "AI_DEL":
                if os.path.exists("checkpoints.sqlite"):
                    try:
                        os.remove("checkpoints.sqlite")
                        reply_msg = "Memory wiped! I have a clean slate."
                    except Exception as e:
                        reply_msg = f"Failed to wipe memory: {e}"
                else:
                    reply_msg = "Memory is already empty."
                reply_to = msg_data.get("to") or sender
                await self._send_text(reply_to, reply_msg)
                return "ok"
            elif text == "AI_LOG":
                from summarize_log import get_summary
                summary = await get_summary()
                reply_to = msg_data.get("to") or sender
                await self._send_text(reply_to, f"Here is your date-wise summary:\n\n{summary}")
                
                # Send raw logs as well
                if os.path.exists("whatsapp_activity_log.md"):
                    with open("whatsapp_activity_log.md", "r", encoding="utf-8") as f:
                        logs = f.read()
                        if logs:
                            await self._send_text(reply_to, f"Raw Logs:\n\n{logs}")
                return "ok"
            
            # For all other outgoing messages (or AI replies), ignore them.
            return "ok"

        # If it's a message.sent event but somehow not fromMe, just ignore it.
        if event_type == "message.sent":
            return "ok"

        # Check Bot State before processing incoming messages
        import os
        if os.path.exists(".bot_state"):
            with open(".bot_state", "r") as f:
                state = f.read().strip()
                if state == "off":
                    LOGGER.info("Bot is OFF. Ignoring message.")
                    return "ok"

        if not sender:
            raise HTTPException(400, detail="Missing 'from' in request payload")

        # Download media if attached
        images = []
        if msg_data.get("hasMedia") or msg_data.get("type") == "image":
            msg_id = msg_data.get("id")
            if isinstance(msg_id, dict):
                msg_id = msg_id.get("id", msg_id)
            
            media_url = f"{OPENWA_API_URL.rstrip('/')}/sessions/{OPENWA_SESSION_ID}/messages/{msg_id}/download"
            headers = {"X-API-Key": OPENWA_API_KEY}
            try:
                async with httpx.AsyncClient() as client:
                    media_resp = await client.get(media_url, headers=headers, timeout=20.0)
                    if media_resp.status_code == 200:
                        import base64
                        b64 = base64.b64encode(media_resp.content).decode("utf-8")
                        content_type = media_resp.headers.get("Content-Type", "image/jpeg")
                        images.append({"data_uri": f"data:{content_type};base64,{b64}"})
                        LOGGER.info("Successfully downloaded and attached media.")
                    else:
                        LOGGER.warning(f"Failed to download media: {media_resp.status_code}")
            except Exception as e:
                LOGGER.error(f"Error downloading media: {e}")

        # Assemble payload for the LangGraph agent
        contact_info = msg_data.get("contact", {})
        sender_name = contact_info.get("pushName") or contact_info.get("name") or sender
        
        if is_group:
            group_info = msg_data.get("group", {})
            group_name = group_info.get("name") or group_info.get("id")
            user_message_text = f"[GROUP({group_name}) MESSAGE from {sender_name}]: {content}"
        else:
            user_message_text = f"[Message from {sender_name}]: {content}"

        input_data = {
            "id": sender,
            "user_message": user_message_text,
        }
        if images:
            input_data["images"] = [
                {"image_url": {"url": img["data_uri"]}} for img in images
            ]

        try:
            # LangGraph processing
            reply = await self.agent.invoke(**input_data)
        except Exception as e:
            LOGGER.error(f"Error invoking LangGraph agent: {e}", exc_info=True)
            return "error"

        # If it was a group message, we process/log it but NEVER send a reply back.
        if is_group:
            LOGGER.info(f"Processed group message from {sender}. No reply will be sent.")
            return "ok"

        # Send reply back via OpenWA API asynchronously
        await self._send_text(sender, reply)
        return "ok"

