import logging
from src.langgraph_whatsapp import config
from langchain_core.messages import HumanMessage
import json
import uuid

LOGGER = logging.getLogger(__name__)

class Agent:
    def __init__(self):
        try:
            self.graph_config = (
                json.loads(config.CONFIG) if isinstance(config.CONFIG, str) else config.CONFIG
            )
        except json.JSONDecodeError as e:
            LOGGER.error(f"Failed to parse CONFIG as JSON: {e}")
            raise

    async def invoke(self, id: str, user_message: str, images: list = None) -> dict:
        """
        Process a user message through the LangGraph agent directly in memory.
        
        Args:
            id: The unique identifier for the conversation
            user_message: The message content from the user
            images: List of dictionaries with image data
            
        Returns:
            str: The result from the LangGraph run
        """
        LOGGER.info(f"Invoking local agent with thread_id: {id}")

        try:
            # Build message content - always use a list for consistent format
            message_content = []
            if user_message:
                message_content.append({
                    "type": "text",
                    "text": user_message
                })

            if images:
                for img in images:
                    if isinstance(img, dict) and "image_url" in img:
                        message_content.append({
                            "type": "image_url",
                            "image_url": img["image_url"]
                        })
            
            # Use HumanMessage for input
            input_dict = {
                "messages": [HumanMessage(content=message_content)]
            }
            
            thread_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, id))
            run_config = {
                "configurable": {"thread_id": thread_id, **self.graph_config},
                "recursion_limit": 25
            }
            
            # Import build_agent here to avoid circular imports if any
            from src.agents.base.graph import build_agent
            from langgraph.errors import GraphRecursionError
            
            async with build_agent() as graph:
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        final_state = await graph.ainvoke(input_dict, config=run_config)
                        
                        if "messages" in final_state and len(final_state["messages"]) > 0:
                            last_msg = final_state["messages"][-1]
                            if hasattr(last_msg, "content"):
                                return last_msg.content
                            elif isinstance(last_msg, dict) and "content" in last_msg:
                                return last_msg["content"]
                        
                        return str(final_state)
                    except GraphRecursionError:
                        LOGGER.warning(f"GraphRecursionError on attempt {attempt + 1}. Retrying...")
                        if attempt == max_retries - 1:
                            LOGGER.error("Max retries reached for GraphRecursionError. Falling back.")
                            return "Sorry, my brain got a bit tangled up processing that! Could you try asking me in a different way?"
        except Exception as e:
            LOGGER.error(f"Error during invoke: {str(e)}", exc_info=True)
            return "Oops, I encountered a minor internal error while thinking about that!"