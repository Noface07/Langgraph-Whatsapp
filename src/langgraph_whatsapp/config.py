from os import environ
import logging
from dotenv import load_dotenv

load_dotenv()

LOGGER = logging.getLogger(__name__)

LANGGRAPH_URL = environ.get("LANGGRAPH_URL")
ASSISTANT_ID = environ.get("LANGGRAPH_ASSISTANT_ID", "agent")
CONFIG = environ.get("CONFIG") or "{}"
OPENWA_API_URL = environ.get("OPENWA_API_URL", "http://localhost:2785/api")
OPENWA_API_KEY = environ.get("OPENWA_API_KEY", "")
OPENWA_SESSION_ID = environ.get("OPENWA_SESSION_ID", "68fc9023-334a-40ce-ac48-e64c1a31ae89")
VIP_IDS = [x.strip() for x in environ.get("VIP_IDS", "").split(",") if x.strip()]