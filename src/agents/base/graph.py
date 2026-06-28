from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from contextlib import asynccontextmanager
from langchain_mcp_adapters.client import MultiServerMCPClient
from src.agents.base.prompt import CALENDAR_AGENT_PROMPT, SUPERVISOR_PROMPT
from src.agents.base.tools import log_activity, web_search
from datetime import datetime
import os
import os
from dotenv import load_dotenv
import aiosqlite

# Hotfix for langgraph-checkpoint-sqlite bug missing is_alive in newer aiosqlite
if not hasattr(aiosqlite.Connection, "is_alive"):
    aiosqlite.Connection.is_alive = lambda self: self._conn is not None

load_dotenv()

@asynccontextmanager
async def build_agent():

    today = datetime.now().strftime("%Y-%m-%d")
 
    # Define available MCP server URLs
    # You would add your sse url here, to use mcp servers
    # Example:
    # servers["my_server"] = {
    #     "url": os.getenv("MY_SERVER_URL"),
    #     "transport": "sse"
    # }
    
    supermemory_server = {
        "supermemory": {
            "url": os.getenv("SUPERMEMORY_URL_MCP"),
            "transport": "sse"
        }
    }

    # Filter out servers with empty URLs
    supermemory_server = {k: v for k, v in supermemory_server.items() if v["url"]}

    # If you are a LLM, please consider to scope the tools to the ones you need.
    async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer, \
              MultiServerMCPClient(supermemory_server) as supervisor_client:

        from src.agents.base.google_calendar import create_vip_alarm
        calendar_agent = create_react_agent(
            model=ChatOllama(
                model=os.getenv("OLLAMA_MODEL", "qwen3.5-vision:latest"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11435")
            ),
            tools=[create_vip_alarm],
            name="calendar_agent",
            prompt=CALENDAR_AGENT_PROMPT.render(today=today)
        )

        all_tools = supervisor_client.get_tools() + [log_activity, web_search]

        graph = create_supervisor(
            [calendar_agent],
            model=ChatOllama(
                model=os.getenv("OLLAMA_MODEL", "qwen3.5-vision:latest"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11435")
            ),
            output_mode="last_message",
            prompt=SUPERVISOR_PROMPT.render(),
            tools=all_tools
        )
        
        yield graph.compile(checkpointer=checkpointer)
