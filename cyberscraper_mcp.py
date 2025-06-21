import os
import json
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, HttpUrl

# Import WebExtractor from CyberScraper
from src.web_extractor import WebExtractor
from src.scrapers.playwright_scraper import ScraperConfig

import socket
import sys

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cyberscraper_mcp.log"),
        logging.StreamHandler(sys.stderr)  # Use stderr instead of stdout
    ]
)


logger = logging.getLogger("CyberScraperMCP")

# Initialize FastAPI
app = FastAPI(
    title="CyberScraper MCP Server",
    description="Model Context Protocol server for CyberScraper 2077's capabilities",
    version="1.0.0",
)

# Keep track of running tasks
tasks_status = {}
extractors_cache = {}

# MCP Protocol Models
class MCPRequest(BaseModel):
    """Base model for MCP requests"""
    id: str = Field(..., description="Request identifier")
    data: Dict[str, Any] = Field(..., description="Request data")

class MCPResponse(BaseModel):
    """Base model for MCP responses"""
    id: str = Field(..., description="Request identifier (echoed from request)")
    data: Dict[str, Any] = Field(..., description="Response data")
    error: Optional[str] = Field(None, description="Error message if request failed")

class ScrapeTaskData(BaseModel):
    """Scraping task data for MCP requests"""
    url: HttpUrl = Field(..., description="URL to scrape")
    instructions: str = Field(..., description="Instructions for what data to extract")
    model: str = Field("gpt-4o-mini", description="Model to use for scraping")
    format: str = Field("json", description="Output format (json, csv, excel, html, sql)")
    openai_key: Optional[str] = Field(None, description="OpenAI API key")
    google_key: Optional[str] = Field(None, description="Google API key")

class ScrapeResponseData(BaseModel):
    """Scraping response data for MCP responses"""
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Task status")

class TaskStatusData(BaseModel):
    """Task status request data for MCP requests"""
    task_id: str = Field(..., description="Task identifier")

def get_or_create_extractor(model: str, openai_key: Optional[str] = None, google_key: Optional[str] = None) -> WebExtractor:
    """Get or create a WebExtractor for the specified model."""
    cache_key = f"{model}_{openai_key}_{google_key}"
    
    if cache_key not in extractors_cache:
        # Set environment variables for API keys
        old_openai_key = os.environ.get("OPENAI_API_KEY")
        old_google_key = os.environ.get("GOOGLE_API_KEY")
        
        try:
            if openai_key:
                os.environ["OPENAI_API_KEY"] = openai_key
            if google_key:
                os.environ["GOOGLE_API_KEY"] = google_key
            
            scraper_config = ScraperConfig(
                headless=True,
                use_stealth=True,
                simulate_human=False,
                use_custom_headers=True,
                hide_webdriver=True,
                bypass_cloudflare=True,
                debug=False,
                timeout=30000,
                wait_for='domcontentloaded',
                use_current_browser=False,
                max_retries=3,
                delay_after_load=2
            )
            
            extractors_cache[cache_key] = WebExtractor(model_name=model, scraper_config=scraper_config)
        finally:
            # Restore original environment variables
            if old_openai_key:
                os.environ["OPENAI_API_KEY"] = old_openai_key
            elif openai_key:
                del os.environ["OPENAI_API_KEY"]
                
            if old_google_key:
                os.environ["GOOGLE_API_KEY"] = old_google_key
            elif google_key:
                del os.environ["GOOGLE_API_KEY"]
    
    return extractors_cache[cache_key]

async def process_scraping_task(task_id: str, url: str, instructions: str, 
                               model: str, format_type: str, openai_key: str = None, 
                               google_key: str = None) -> None:
    """Process a scraping task in the background."""
    try:
        tasks_status[task_id]["status"] = "processing"
        
        # Validate API keys based on model
        if model.startswith(("gpt-", "text-")) and not openai_key:
            raise ValueError("OpenAI API key is required for OpenAI models")
        if model.startswith("gemini-") and not google_key:
            raise ValueError("Google API key is required for Gemini models")
        
        # Get or create extractor
        web_extractor = get_or_create_extractor(model, openai_key, google_key)
        
        # First, fetch the URL content
        logger.info(f"Task {task_id}: Fetching content from {url}")
        fetch_response = await web_extractor.process_query(url)
        logger.info(f"Task {task_id}: Fetch response: {fetch_response[:100]}...")
        
        # Now process the instructions
        logger.info(f"Task {task_id}: Processing instructions: {instructions}")
        
        # Determine if format is specified in the instructions
        format_in_instructions = any(f in instructions.lower() for f in ['json', 'csv', 'excel', 'html', 'sql'])
        
        # If format is not in instructions, append it
        task_instructions = instructions
        if not format_in_instructions:
            task_instructions = f"{instructions} in {format_type} format"
        
        # Execute the instructions
        result = await web_extractor.process_query(task_instructions)
        
        # Process the result
        data = result
        if isinstance(result, tuple) and len(result) == 2:
            # Result contains data and DataFrame
            content, df = result
            
            if format_type == 'csv':
                data = df.to_csv(index=False)
            elif format_type == 'json':
                data = df.to_json(orient='records', indent=2)
            elif format_type == 'excel':
                # For API, we can't return Excel binary directly, so convert to JSON
                data = df.to_json(orient='records', indent=2)
                format_type = 'json'  # Update format to indicate conversion
        
        # Update task status
        tasks_status[task_id] = {
            "task_id": task_id,
            "status": "completed",
            "url": url,
            "format": format_type,
            "data": data,
            "error": None,
            "completed_at": datetime.now().isoformat()
        }
        
        logger.info(f"Task {task_id} completed successfully")
    except Exception as e:
        logger.error(f"Error processing task {task_id}: {str(e)}", exc_info=True)
        tasks_status[task_id] = {
            "task_id": task_id,
            "status": "failed",
            "url": url,
            "format": format_type,
            "data": None,
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        }

@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest, background_tasks: BackgroundTasks):
    """Model Context Protocol endpoint for all operations"""
    try:
        # Determine the operation type based on the data structure
        if "operation" not in request.data:
            return MCPResponse(
                id=request.id,
                data={},
                error="Missing 'operation' field in request data"
            )
        
        operation = request.data["operation"]
        
        if operation == "scrape":
            # Validate required fields
            required_fields = ["url", "instructions"]
            for field in required_fields:
                if field not in request.data:
                    return MCPResponse(
                        id=request.id,
                        data={},
                        error=f"Missing required field: {field}"
                    )
            
            # Extract parameters
            url = request.data["url"]
            instructions = request.data["instructions"]
            model = request.data.get("model", "gpt-4o-mini")
            format_type = request.data.get("format", "json")
            openai_key = request.data.get("openai_key")
            google_key = request.data.get("google_key")
            
            # Validate API keys based on model
            if model.startswith(("gpt-", "text-")) and not openai_key:
                return MCPResponse(
                    id=request.id,
                    data={},
                    error="OpenAI API key is required for OpenAI models"
                )
            if model.startswith("gemini-") and not google_key:
                return MCPResponse(
                    id=request.id,
                    data={},
                    error="Google API key is required for Gemini models"
                )
            
            # Generate task ID
            task_id = str(uuid.uuid4())
            
            # Initialize task status
            tasks_status[task_id] = {
                "task_id": task_id,
                "status": "pending",
                "url": url,
                "format": format_type,
                "data": None,
                "error": None,
                "completed_at": None
            }
            
            # Start processing in the background
            background_tasks.add_task(
                process_scraping_task,
                task_id,
                url,
                instructions,
                model,
                format_type,
                openai_key,
                google_key
            )
            
            # Return response
            return MCPResponse(
                id=request.id,
                data={
                    "task_id": task_id,
                    "status": "pending",
                    "message": "Task created and processing will begin shortly"
                }
            )
        
        elif operation == "get_task_status":
            # Validate required fields
            if "task_id" not in request.data:
                return MCPResponse(
                    id=request.id,
                    data={},
                    error="Missing required field: task_id"
                )
            
            task_id = request.data["task_id"]
            
            # Check if task exists
            if task_id not in tasks_status:
                return MCPResponse(
                    id=request.id,
                    data={},
                    error=f"Task with ID {task_id} not found"
                )
            
            # Return task status
            return MCPResponse(
                id=request.id,
                data=tasks_status[task_id]
            )
        
        elif operation == "health_check":
            # Simple health check
            return MCPResponse(
                id=request.id,
                data={"status": "healthy", "timestamp": datetime.now().isoformat()}
            )
        
        else:
            # Unknown operation
            return MCPResponse(
                id=request.id,
                data={},
                error=f"Unknown operation: {operation}"
            )
    
    except Exception as e:
        logger.error(f"Error processing MCP request: {str(e)}", exc_info=True)
        return MCPResponse(
            id=request.id,
            data={},
            error=f"Internal server error: {str(e)}"
        )

@app.get("/")
async def root():
    """Root endpoint with server information."""
    return {
        "name": "CyberScraper MCP Server",
        "version": "1.0.0",
        "description": "Model Context Protocol server for CyberScraper 2077",
        "endpoint": "/mcp"
    }

if __name__ == "__main__":
    port = 8000  
    if is_port_in_use(port):
        # Write to stderr instead of stdout to avoid interfering with MCP communication
        print(f"Port {port} is already in use. Assuming server is already running.", file=sys.stderr)
        sys.exit(0)
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)