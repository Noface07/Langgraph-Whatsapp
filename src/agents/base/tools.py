import os
from datetime import datetime
from langchain_core.tools import tool

@tool
def log_activity(summary: str) -> str:
    """Logs an activity summary to a local markdown file so the user can review it later. Use this tool to save important messages or interaction summaries."""
    log_file = "whatsapp_activity_log.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"- **{timestamp}**: {summary}\n")
        return "Activity logged successfully."
    except Exception as e:
        return f"Failed to log activity: {str(e)}"
