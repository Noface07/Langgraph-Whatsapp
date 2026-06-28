# LangGraph WhatsApp AI Assistant 🤖📱

A highly resilient, privacy-first, and fully autonomous WhatsApp AI Assistant powered by **LangGraph**, local LLMs (**Ollama**), and **WAHA (WhatsApp HTTP API)**.

Unlike standard chatbots, this agent acts as a true personal assistant. It intelligently filters messages, silently summarizes group chats, remembers past conversations, analyzes images, and can be completely controlled remotely from your own WhatsApp.

---

## 🌟 Key Features

* **🧠 Persistent Memory & Semantic RAG**: 
  * Uses `langgraph-checkpoint-sqlite` to maintain long-term conversation history for every contact.
  * Silently logs activities into a local **ChromaDB** vector database. Powered by the local `nomic-embed-text` embedding model, this allows you to perform semantic searches over your history.
* **👁️ Vision & Multimodality**: Built-in support for `qwen3.5-vision` (via Ollama). Send an image to your WhatsApp, and the AI will analyze it.
* **🌐 Agentic Web Search**: Equipped with a DuckDuckGo web search tool, allowing the AI to autonomously browse the internet for up-to-date facts when it doesn't know the answer.
* **🚨 VIP Google Calendar Alarms**: Specify VIP contact IDs in your `.env`. If they message you, the AI directly interfaces with the **Google Calendar API** to schedule an immediate 1-minute alarm to vibrate your phone and notify you!
* **🛡️ Smart Group Chat Handling**: The agent recognizes group chats, silently logs the contents to ChromaDB, but strictly *never* auto-replies in groups.
* **📱 Remote WhatsApp Control**: Control your server directly from your phone! Text yourself special commands:
  * `AI_OFF` / `AI_ON` - Instantly pauses or resumes the AI.
  * `AI_LOG <query>` - Generates a summary. You can ask semantic questions like "AI_LOG what did moneycontrol say today?" and it will query the RAG system.
  * `AI_DEL` - Forcefully wipes the memory for a clean slate.
* **🔁 Bulletproof Resilience**:
  * **LangGraph Retries**: Gracefully intercepts `GraphRecursionError` and auto-retries hallucinated tool calls.
  * **Proactive Polling Daemon**: A background task polls the WAHA API every 60 seconds. If the WhatsApp session crashes or hangs in a "disconnected" state, it gracefully kills and revives the session.

---

## 🏗️ Architecture

1. **WAHA (WhatsApp HTTP API)**: Bridge to WhatsApp, listening to webhooks.
2. **FastAPI**: Asynchronous webhook receiver and background polling daemon.
3. **LangGraph**: The core supervisor agent routing messages and orchestrating tools (Calendar, Web Search, RAG).
4. **Ollama**: Local inference engine for fast, private AI processing & embeddings.
5. **ChromaDB & SQLite**: Vector database for semantic RAG searches and persistent checkpointer for LangGraph state.

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+**
- **Ollama** installed and running locally with your model of choice (e.g., `qwen3.5-vision:latest`).
- **WAHA / OpenWA** instance running (usually via Docker).

### 2. Installation

Clone the repository and install the required dependencies using `uv` (or pip):

```bash
git clone https://github.com/<YOUR_USERNAME>/langgraph-whatsapp-agent.git
cd langgraph-whatsapp-agent
uv sync
```

### 3. Configuration
Copy the example environment file and fill in your details:
```bash
cp .env.example .env
```
Ensure your `.env` contains the correct `OPENWA_API_URL` and `OPENWA_SESSION_ID`.

### 4. Running the Agent
Start the FastAPI webhook server:
```bash
python -m src.langgraph_whatsapp.server
```

*(Alternatively, use the provided `run.bat` or `start.bat` scripts if you are on Windows).*

---

## 🛠️ Modifying the Prompt

You can customize the bot's personality by editing `src/agents/base/prompt.py`. By default, it is configured to act extremely casually, never announce itself as an AI, and handle messages exactly like a human taking notes for you while you are busy.

---

## 📜 License

This project is licensed under the MIT License - see the `src/LICENSE` file for details.