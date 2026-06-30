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
        
        health_url = f"{OPENWA_API_URL.rstrip('/')}/health"
        try:
            health_resp = await client.get(health_url, timeout=10.0)
            if health_resp.status_code != 200:
                LOGGER.error(f"WAHA Engine is DOWN. Health check failed: {health_resp.status_code}. Aborting restart.")
                return
        except Exception as e:
            LOGGER.error(f"Failed to reach WAHA Health API: {e}. Aborting restart.")
            return

        stop_url = f"{OPENWA_API_URL.rstrip('/')}/sessions/{OPENWA_SESSION_ID}/stop"
        start_url = f"{OPENWA_API_URL.rstrip('/')}/sessions/{OPENWA_SESSION_ID}/start"
        
        try:
            await client.post(stop_url, headers=headers, timeout=10.0)
        except Exception:
            pass
            
        try:
            start_resp = await client.post(start_url, headers=headers, timeout=30.0)
            if start_resp.status_code in [200, 201]:
                LOGGER.info("Session restarted successfully. Waiting for WhatsApp client to connect (this may take a few seconds)...")
                
                import asyncio
                is_connected = False
                for _ in range(15):
                    await asyncio.sleep(2.0)
                    status_url = f"{OPENWA_API_URL.rstrip('/')}/sessions/{OPENWA_SESSION_ID}"
                    try:
                        status_resp = await client.get(status_url, headers=headers, timeout=5.0)
                        if status_resp.status_code == 200:
                            status_data = status_resp.json()
                            status_str = status_data.get("status", "").upper()
                            if status_str not in ["STARTING", "STOPPED", "FAILED", "DISCONNECTED"]:
                                # Usually 'WORKING', 'CONNECTED', or 'AUTHENTICATED'
                                is_connected = True
                                break
                    except Exception as e:
                        LOGGER.warning(f"Failed to poll status: {e}")
                
                if not is_connected:
                    LOGGER.error("WhatsApp client did not connect in time after restart. Aborting retry.")
                    return
                    
                LOGGER.info("WhatsApp client is ready! Retrying message send...")
                retry_resp = await client.post(send_url, json=send_payload, headers=headers, timeout=30.0)
                if retry_resp.status_code >= 400:
                    LOGGER.error(f"Failed to send OpenWA message after session restart: {retry_resp.status_code} {retry_resp.text}")
                else:
                    LOGGER.info(f"Successfully sent reply to {chat_id} after session restart")
            elif start_resp.status_code == 400 and "already started" in start_resp.text.lower():
                LOGGER.info("Session was already started, no need to restart.")
            else:
                LOGGER.error(f"Failed to restart session: {start_resp.status_code} {start_resp.text}")
        except Exception as e:
            LOGGER.error(f"Error during session restart fallback: {e}")

    async def force_restart_session(self):
        import httpx
        LOGGER.info("Proactively restarting the OpenWA session...")
        headers = {"X-API-Key": OPENWA_API_KEY}
        async with httpx.AsyncClient() as client:
            stop_url = f"{OPENWA_API_URL.rstrip('/')}/sessions/{OPENWA_SESSION_ID}/stop"
            start_url = f"{OPENWA_API_URL.rstrip('/')}/sessions/{OPENWA_SESSION_ID}/start"
            
            try:
                await client.post(stop_url, headers=headers, timeout=10.0)
            except Exception:
                pass
                
            try:
                start_resp = await client.post(start_url, headers=headers, timeout=30.0)
                if start_resp.status_code in [200, 201]:
                    LOGGER.info("Successfully restarted OpenWA session proactively!")
                elif start_resp.status_code == 400 and "already started" in start_resp.text.lower():
                    LOGGER.info("OpenWA session is already started.")
                else:
                    LOGGER.error(f"Failed to restart OpenWA session. Status: {start_resp.status_code}")
            except Exception as e:
                LOGGER.error(f"Error during proactive restart request: {e}")

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
            elif text.startswith("AI_LOG"):
                parts = content.strip().split(" ", 1)
                log_cmd = parts[0].upper()
                query_str = parts[1] if len(parts) > 1 else None
                
                date_str = None
                if log_cmd.startswith("AI_LOG_") and len(log_cmd) == 15: # AI_LOG_DDMMYYYY
                    date_part = log_cmd[7:]
                    try:
                        from datetime import datetime
                        date_str = datetime.strptime(date_part, "%d%m%Y").strftime("%Y-%m-%d")
                    except ValueError:
                        pass
                
                from summarize_log import get_summary
                summary = await get_summary(date_str, query_str)
                reply_to = msg_data.get("to") or sender
                await self._send_text(reply_to, f"Here is your log summary:\n\n{summary}")
                return "ok"
            
            # For all other outgoing messages (or AI replies), ignore them.
            return "ok"

        # If it's a message.sent event but somehow not fromMe, just ignore it.
        if event_type == "message.sent":
            return "ok"

        # Check if message is of type unknown, which can cause loops if empty
        if msg_data.get("type") == "unknown":
            LOGGER.info(f"Ignoring 'unknown' type message from {sender} to prevent loops.")
            return "ok"

        # Check Bot State before processing incoming messages
        import os
        state = "on"
        if os.path.exists(".bot_state"):
            with open(".bot_state", "r") as f:
                state = f.read().strip()

        if not sender:
            raise HTTPException(400, detail="Missing 'from' in request payload")

        # Download media if attached
        images = []
        document_text = ""
        if msg_data.get("hasMedia") or msg_data.get("type") in ["image", "document"]:
            media_url = None
            if "media" in msg_data and isinstance(msg_data["media"], dict):
                media_url = msg_data["media"].get("url")
            
            if not media_url:
                LOGGER.warning("Message has media but no media.url was provided in the webhook payload. Attempting fallback download endpoint.")
                message_id = msg_data.get("id")
                if isinstance(message_id, dict):
                    message_id = message_id.get("id")
                
                if message_id:
                    media_url = f"{OPENWA_API_URL.rstrip('/')}/sessions/{OPENWA_SESSION_ID}/messages/{message_id}/media"

            if media_url:
                # Rewrite media_url to use the host-accessible OPENWA_API_URL base (fixes Docker localhost:3000 / waha:3000 issues)
                from urllib.parse import urlparse, urlunparse
                parsed_media = urlparse(media_url)
                parsed_api = urlparse(OPENWA_API_URL)
                media_url = urlunparse(parsed_media._replace(scheme=parsed_api.scheme, netloc=parsed_api.netloc))

                headers = {"X-API-Key": OPENWA_API_KEY}
                try:
                    async with httpx.AsyncClient() as client:
                        media_resp = await client.get(media_url, headers=headers, timeout=30.0)
                    if media_resp.status_code == 200:
                        content_type = media_resp.headers.get("Content-Type", "")
                        
                        if "image" in content_type:
                            import base64
                            b64 = base64.b64encode(media_resp.content).decode("utf-8")
                            images.append({"data_uri": f"data:{content_type};base64,{b64}"})
                            LOGGER.info("Successfully downloaded and attached image media.")
                        elif "pdf" in content_type:
                            import fitz # PyMuPDF
                            doc = fitz.open(stream=media_resp.content, filetype="pdf")
                            text_pages = []
                            for page in doc:
                                text_pages.append(page.get_text())
                            document_text = "\n".join(text_pages)
                            LOGGER.info("Successfully parsed PDF document.")
                        else:
                            try:
                                document_text = media_resp.content.decode("utf-8")
                                LOGGER.info("Successfully parsed plain text document.")
                            except Exception:
                                LOGGER.warning(f"Unsupported document type: {content_type}")
                    else:
                        LOGGER.warning(f"Failed to download media: {media_resp.status_code}")
                except Exception as e:
                    LOGGER.error(f"Error downloading media: {e}")

        if not content and not images and not document_text:
            LOGGER.info(f"Ignoring message with empty content and no media from {sender} to prevent loops.")
            return "ok"

        # Assemble payload for the LangGraph agent
        contact_info = msg_data.get("contact", {})
        sender_name = contact_info.get("pushName") or contact_info.get("name") or sender
        
        from src.langgraph_whatsapp.config import VIP_IDS
        
        actual_sender_id = msg_data.get("author") or sender
        def _get_base_id(full_id):
            return str(full_id).split('@')[0]
            
        clean_vips = [_get_base_id(v) for v in VIP_IDS]
        is_vip = _get_base_id(actual_sender_id) in clean_vips

        if is_vip:
            user_message_text = f"[VIP MESSAGE from {sender_name}]: {content}"
        elif is_group:
            group_info = msg_data.get("group", {})
            group_name = group_info.get("name") or group_info.get("id")
            user_message_text = f"[GROUP({group_name}) MESSAGE from {sender_name}]: {content}"
        else:
            user_message_text = f"[Message from {sender_name}]: {content}"

        if document_text:
            user_message_text += f"\n\n[ATTACHED DOCUMENT TEXT]:\n{document_text}"

        try:
            from src.agents.base.tools import do_log_activity
            do_log_activity(f"Incoming message: {user_message_text}")
        except Exception as e:
            LOGGER.error(f"Failed to auto-log incoming message: {e}")

        # If the message is from before the server started, skip agent processing
        msg_timestamp = msg_data.get("timestamp")
        if msg_timestamp:
            try:
                msg_ts = float(msg_timestamp)
                if msg_ts > 1e11:
                    msg_ts /= 1000.0
                from src.langgraph_whatsapp.config import STARTUP_TIME
                if msg_ts < STARTUP_TIME:
                    LOGGER.info(f"Old message from {sender} was logged but will not be processed or replied to.")
                    return "ok"
            except (ValueError, TypeError):
                pass

        if state == "off":
            user_message_text += "\n\n[SYSTEM INSTRUCTION]: The bot is currently PAUSED. You are in SILENT LISTENER mode. DO NOT use google_calendar or web_search tools. Your ONLY job is to use the log_activity tool to record this."

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

        # If it was a group message, or the bot is OFF, we process/log it but NEVER send a reply back.
        if is_group or state == "off":
            LOGGER.info(f"Processed message from {sender} (Group: {is_group}, State: {state}). No reply will be sent.")
            return "ok"

        # Send reply back via OpenWA API asynchronously
        await self._send_text(sender, reply)
        return "ok"

