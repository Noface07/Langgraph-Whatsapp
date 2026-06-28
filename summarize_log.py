import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

async def get_summary() -> str:
    log_file = "whatsapp_activity_log.md"
    if not os.path.exists(log_file):
        return "No activity log found yet."

    with open(log_file, "r", encoding="utf-8") as f:
        log_content = f.read().strip()
        
    if not log_content:
        return "Activity log is currently empty."
        
    model_name = os.getenv("OLLAMA_MODEL", "qwen3.5-vision:latest")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11435")
    
    model = ChatOllama(
        model=model_name,
        base_url=base_url
    )
    
    prompt = f"""
    You are an AI assistant tasked with summarizing an activity log.
    CONTEXT: These logs belong to Yuvraj Soni's personal WhatsApp AI Assistant. The logs contain summaries of messages sent by Yuvraj's friends/family to his WhatsApp account, which were handled by the AI assistant while Yuvraj was away.
    
    Please provide a concise 2-3 paragraph summary of the following log. 
    Crucially, organize and order the summary DATE-WISE so Yuvraj can easily see what happened chronologically.
    Identify people by their names as listed in the log. Do not use generic terms like "the user" when referring to the person who sent the message. 
    CRITICAL RULE: DO NOT assume relationships, events, or ownership. If the log says "Happy anniversary Raju and Asha", do NOT summarize it as Yuvraj's anniversary or Yuvraj's spouse. Only state exactly what is written.
    Keep it easy to read and focus on the most important messages or events.
    
    Here is the raw log data:
    {log_content}
    """
    
    messages = [
        SystemMessage(content="You are a helpful assistant that writes clear, concise summaries."),
        HumanMessage(content=prompt)
    ]
    
    try:
        response = await model.ainvoke(messages)
        return response.content
    except Exception as e:
        return f"Error generating summary: {e}"

def main():
    import asyncio
    load_dotenv()
    print("Reading log and generating a date-wise summary using Ollama...\n")
    summary = asyncio.run(get_summary())
    print("=== WHATSAPP ACTIVITY SUMMARY ===")
    print(summary)
    print("=================================")

if __name__ == "__main__":
    main()
