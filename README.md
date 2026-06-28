# LangGraph WhatsApp Agent

A template for building WhatsApp agents using LangGraph and Twilio. This project enables you to deploy AI agents that interact with users via WhatsApp, process messages and images, and invoke custom graph-based agents hosted on the LangGraph Platform.

It provides a foundation for building scalable, secure, and maintainable AI agent services.

Fork this repo and iterate to create your production-ready solution.

![Architecture Diagram](./docs/app_architecture_v0.1.0.png)

## Features

- Create custom LangGraph-powered agents for WhatsApp
- Support for multi-agents with supervisor-based architecture
- Integration with Model Context Protocol (MCP) servers (Supermemory, Sapier, etc.)
- Support for image processing and multimodal interactions
- Persistent conversation state across messages
- Request validation for security
- Comprehensive observability via LangSmith
- Easy deployment with LangGraph Platform

## Stack

- **WhatsApp Integration**: Twilio API for messaging and multimedia handling
- **Agent Framework**: LangGraph (by LangChain) as the MCP client and multi-agent system using langgraph_supervisor
- **Models**: Supports Google Gemini, OpenAI GPT models, and more
- **MCP Servers**:
  Using langchain-mcp-adapters
  - Supermemory
  - Zapier for access to thousands of apps and integrations (Google, Slack, Spotify, etc.)
- **Observability**: Complete tracing with LangSmith
- **Deployment**: LangGraph Platform for simplified production hosting

## Prerequisites

- Twilio account with WhatsApp integration
- API key for LLM access (OpenAI, Google, etc.)
- LangGraph Platform access
- (Optional) MCP server configurations

## Getting Started

1. Fork this repository to start your own project
2. Build your agent using the template structure
3. Deploy to LangGraph Platform
![Langggraph Platform](./docs/langgraph-platform_config.png)
4. Configure Twilio webhook to point to your LangGraph deployment URL (/whatsapp)
![Twilio](./docs/twilio_config.png)

## License

This project is licensed under the terms included in the LICENSE file.