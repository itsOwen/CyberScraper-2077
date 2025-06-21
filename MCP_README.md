# CyberScraper MCP Server and Client

A Model Context Protocol implementation for the CyberScraper 2077 web scraping system.

## What is Model Context Protocol (MCP)?

The Model Context Protocol (MCP) is a standardized way for applications to communicate with AI models and AI-powered services. It provides a consistent interface for sending requests and receiving responses, making it easier to integrate AI capabilities into applications.

## Overview

This implementation consists of two main components:

1. **MCP Server**: A FastAPI server that exposes the CyberScraper functionality through a standardized MCP endpoint
2. **MCP Client**: A Python client library for interacting with the MCP server

The MCP interface allows for easy integration with other systems and services that support the Model Context Protocol.

## MCP Server

### Features

- Single `/mcp` endpoint for all operations
- Standardized request and response format
- Support for multiple AI models (OpenAI, Google Gemini)
- Background task processing
- Task status tracking

### Installation and Deployment

```bash
pip install -r requirements.txt
pip install fastapi uvicorn
python cyberscraper_mcp.py
```

The server will be available at `http://localhost:8000`.

### Protocol Specification

All operations use the same endpoint (`/mcp`) with a consistent request and response format:

**Request:**
```json
{
  "id": "request-uuid",
  "data": {
    "operation": "operation-name",
    ...operation-specific fields...
  }
}
```

**Response:**
```json
{
  "id": "request-uuid",
  "data": {
    ...operation-specific response...
  },
  "error": null
}
```

### Operations

#### 1. Scrape

Submit a new scraping task.

**Request:**
```json
{
  "id": "request-uuid",
  "data": {
    "operation": "scrape",
    "url": "https://example.com",
    "instructions": "Extract all product names and prices",
    "model": "gpt-4o-mini",
    "format": "json",
    "openai_key": "your-openai-key",
    "google_key": "your-google-key"
  }
}
```

**Response:**
```json
{
  "id": "request-uuid",
  "data": {
    "task_id": "task-uuid",
    "status": "pending",
    "message": "Task created and processing will begin shortly"
  },
  "error": null
}
```

#### 2. Get Task Status

Check the status of a scraping task.

**Request:**
```json
{
  "id": "request-uuid",
  "data": {
    "operation": "get_task_status",
    "task_id": "task-uuid"
  }
}
```

**Response:**
```json
{
  "id": "request-uuid",
  "data": {
    "task_id": "task-uuid",
    "status": "completed",
    "url": "https://example.com",
    "format": "json",
    "data": [...scraped data...],
    "error": null,
    "completed_at": "2025-03-22T14:30:45.123456"
  },
  "error": null
}
```

#### 3. Health Check

Check the health of the MCP server.

**Request:**
```json
{
  "id": "request-uuid",
  "data": {
    "operation": "health_check"
  }
}
```

**Response:**
```json
{
  "id": "request-uuid",
  "data": {
    "status": "healthy",
    "timestamp": "2025-03-22T14:30:45.123456"
  },
  "error": null
}
```

## MCP Client

The MCP Client provides a simple Python interface for interacting with the MCP Server.

### Installation

```bash
# The client is just a single file - copy it to your project
cp cyberscraper_mcp_client.py /your/project/directory/
```

### Basic Usage

```python
from cyberscraper_mcp_client import CyberScraperMCPClient

# Create client
client = CyberScraperMCPClient("http://localhost:8000")

# Check server health
health = client.health_check()
print(f"Server health: {health['status']}")

# Scrape and wait for result