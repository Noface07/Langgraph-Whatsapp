import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

async def get_summary(date_str: str = None, query_str: str = None) -> str:
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        
    db_file = "logs.sqlite"
    if not os.path.exists(db_file) and not os.path.exists("./chroma_db"):
        return f"No activity logs found yet for {date_str}."

    log_content = ""
    if query_str:
        try:
            from langchain_chroma import Chroma
            from langchain_ollama import OllamaEmbeddings
            embeddings = OllamaEmbeddings(
                model="nomic-embed-text:latest",
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11435")
            )
            vector_store = Chroma(
                collection_name="whatsapp_logs",
                embedding_function=embeddings,
                persist_directory="./chroma_db"
            )
            filter_dict = {"date": date_str} if date_str else None
            results = vector_store.similarity_search(query_str, k=10, filter=filter_dict)
            if not results:
                return f"No relevant logs found for your query on {date_str}."
            log_content = "\\n".join([r.page_content for r in results])
        except Exception as e:
            return f"Error searching vector store: {e}"
    else:
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT timestamp, summary FROM activity_logs WHERE date = ?", (date_str,))
            rows = cursor.fetchall()
            conn.close()
            if not rows:
                return f"Activity log is currently empty for the date: {date_str}."
            log_content = "\\n".join([f"- **{r[0]}**: {r[1]}" for r in rows])
        except Exception as e:
            return f"Database error: {e}"
        
    model_name = os.getenv("OLLAMA_MODEL", "qwen3.5-vision:latest")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11435")
    
    model = ChatOllama(
        model=model_name,
        base_url=base_url
    )
    
    base_prompt = f"""
    You are an AI assistant tasked with summarizing an activity log for {date_str}.
    CONTEXT: These logs belong to Yuvraj Soni's personal WhatsApp AI Assistant. The logs contain summaries of messages sent by Yuvraj's friends/family to his WhatsApp account, which were handled by the AI assistant while Yuvraj was away.
    
    Crucially, organize and order the summary DATE-WISE so Yuvraj can easily see what happened chronologically.
    Identify people by their names as listed in the log. Do not use generic terms like "the user" when referring to the person who sent the message. 
    CRITICAL RULE: DO NOT assume relationships, events, or ownership. If the log says "Happy anniversary Raju and Asha", do NOT summarize it as Yuvraj's anniversary or Yuvraj's spouse. Only state exactly what is written.
    """
    
    if query_str:
        base_prompt += f"\\n\\nUSER QUESTION: {query_str}\\nPlease answer the user's question based ONLY on the provided logs. Do not generate a general summary unless requested."
    else:
        base_prompt += "\\n\\nPlease provide a concise 2-3 paragraph summary of the logs. Keep it easy to read and focus on the most important messages or events."

    base_prompt += f"\\n\\nHere is the raw log data for {date_str}:\\n{log_content}"
    
    messages = [
        SystemMessage(content="You are a helpful assistant that writes clear, concise summaries from logs."),
        HumanMessage(content=base_prompt)
    ]
    
    try:
        response = await model.ainvoke(messages)
        return response.content
    except Exception as e:
        return f"Error generating summary: {e}"

def main():
    import asyncio
    import sys
    load_dotenv()
    
    date_arg = None
    query_arg = None
    if len(sys.argv) > 1:
        date_arg = sys.argv[1]
    if len(sys.argv) > 2:
        query_arg = " ".join(sys.argv[2:])
        
    print(f"Reading log and generating a date-wise summary using Ollama (Date: {date_arg or 'Today'})...\\n")
    summary = asyncio.run(get_summary(date_arg, query_arg))
    print("=== WHATSAPP ACTIVITY SUMMARY ===")
    print(summary)
    print("=================================")

if __name__ == "__main__":
    main()
