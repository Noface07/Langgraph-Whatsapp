import os
from datetime import datetime
from langchain_core.tools import tool

import sqlite3

def _init_db():
    conn = sqlite3.connect("logs.sqlite")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            timestamp TEXT,
            summary TEXT
        )
    """)
    conn.commit()
    conn.close()

def do_log_activity(summary: str) -> str:
    _init_db()
    
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        conn = sqlite3.connect("logs.sqlite")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO activity_logs (date, timestamp, summary) VALUES (?, ?, ?)",
            (date_str, timestamp_str, summary)
        )
        conn.commit()
        conn.close()
        
        try:
            from langchain_chroma import Chroma
            from langchain_ollama import OllamaEmbeddings
            import os
            
            embeddings = OllamaEmbeddings(
                model="nomic-embed-text:latest",
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11435")
            )
            vector_store = Chroma(
                collection_name="whatsapp_logs",
                embedding_function=embeddings,
                persist_directory="./chroma_db"
            )
            
            vector_store.add_texts(
                texts=[f"[{timestamp_str}] {summary}"],
                metadatas=[{"date": date_str, "timestamp": timestamp_str}]
            )
        except Exception as ve:
            print(f"Warning: Failed to log to ChromaDB: {ve}")
            
        return "Activity logged successfully."
    except Exception as e:
        return f"Failed to log activity: {str(e)}"

@tool
def log_activity(summary: str) -> str:
    """Logs an activity summary to a local SQLite database so the user can review it later. Use this tool to save important messages or interaction summaries."""
    return do_log_activity(summary)

@tool
def web_search(query: str) -> str:
    """Searches the internet for the given query and returns a summary of the top results. Use this tool when you need to find up-to-date information, news, or facts that you do not know."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            if not results:
                return "No results found on the web."
            
            output = ""
            for r in results:
                output += f"Title: {r.get('title')}\nSnippet: {r.get('body')}\n\n"
            return output
    except Exception as e:
        return f"Web search failed: {e}"
