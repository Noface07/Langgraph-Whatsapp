# LangGraph WhatsApp AI Assistant 🤖📱

A highly resilient, privacy-first, and fully autonomous WhatsApp AI Assistant powered by **LangGraph**, local LLMs (**Ollama**), and **WAHA (WhatsApp HTTP API)**.

Unlike standard chatbots, this agent acts as a true personal assistant. It intelligently filters messages, silently summarizes group chats, remembers past conversations, analyzes images, and can be completely controlled remotely from your own WhatsApp.

---

## 🌟 Key Features

* **🧠 Persistent Memory**: Uses `langgraph-checkpoint-sqlite` to maintain long-term conversation history for every individual contact.
* **👁️ Vision & Multimodality**: Built-in support for `qwen3.5-vision` (via Ollama). Send an image to your WhatsApp, and the AI will download the media, analyze it, and reply intelligently.
* **🛡️ Smart Group Chat Handling**: The agent recognizes group chats. It will silently log the contents for your reference but is strictly programmed *never* to embarrass you by auto-replying in groups.
* **📱 Remote WhatsApp Control**: Control your server directly from your phone! Text yourself special commands:
  * `AI_OFF` - Instantly pauses the AI.
  * `AI_ON` - Resumes AI operation.
  * `AI_LOG` - Generates and sends you a chronological, date-wise summary of everything the bot handled while you were away.
  * `AI_DEL` - Forcefully wipes the SQLite memory database for a clean slate.
* **🔁 Bulletproof Resilience**:
  * **LangGraph Retries**: If the local LLM hallucinates or gets stuck in a logic loop, LangGraph gracefully intercepts the `GraphRecursionError` and auto-retries.
  * **Session Auto-Restart**: If the OpenWA/WAHA connection drops, the bot automatically pings the WAHA API to jumpstart the session and seamlessly retries sending the message.
* **🔒 100% Local & Private**: All AI processing runs completely locally on your hardware via Ollama. No data is sent to OpenAI or third-party cloud providers.

---

## 🏗️ Architecture

1. **WAHA (WhatsApp HTTP API)**: Provides the bridge to WhatsApp. Listens to incoming webhooks and handles outgoing messages.
2. **FastAPI**: Acts as the fast, asynchronous webhook receiver for WAHA.
3. **LangGraph**: The core brain. Acts as a supervisor agent that routes messages, decides when to use tools (like logging), and maintains state.
4. **Ollama**: Local inference engine for fast, private AI processing.
5. **SQLite**: Persistent database checkpointer for LangGraph memory.

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