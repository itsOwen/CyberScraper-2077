from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any, List, Union
import asyncio
import uuid
import logging
import os
from datetime import datetime

# Import WebExtractor from CyberScraper
from src.web_extractor import WebExtractor
from src.scrapers.playwright_scraper import ScraperConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cyberscraper_api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CyberScraperAPI")

# Initialize FastAPI
app = FastAPI(
    title="CyberScraper API",
    description="API for web scraping using CyberScraper 2077's capabilities",
    version="1.0.0",
)

# Keep track of running tasks
tasks_status = {}
extractors_cache = {}

# Models for API requests and responses
class ScraperTask(BaseModel):
    url: HttpUrl = Field(..., description="URL to scrape")
    instructions: str = Field(..., description="Instructions for what data to extract")
    model: str = Field("gpt-4o-mini", description="Model to use for scraping (e.g., gpt-4o-mini, gpt-3.5-turbo, gemini-pro)")
    format: str = Field("json", description="Output format (json, csv, excel, html, sql)")

class TaskResponse(BaseModel):
    task_id: str = Field(..., description="Unique task ID for tracking")
    status: str = Field(..., description="Task status (pending, processing, completed, failed)")
    message: str = Field(..., description="Informational message about the task")

class TaskResult(BaseModel):
    task_id: str = Field(..., description="Task ID")
    status: str = Field(..., description="Task status")
    url: HttpUrl = Field(..., description="URL that was scraped")
    format: str = Field(..., description="Output format")
    data: Any = Field(None, description="Scraped data (if available)")
    error: Optional[str] = Field(None, description="Error message (if status is 'failed')")
    completed_at: Optional[datetime] = Field(None, description="Time when the task was completed")

def get_api_key(x_openai_key: Optional[str] = Header(None), x_google_key: Optional[str] = Header(None)):
    """Get API keys from headers"""
    return {"openai_key": x_openai_key, "google_key": x_google_key}

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

async def process_scraping_task(task_id: str, task: ScraperTask, api_keys: Dict[str, str]):
    """Process a scraping task in the background."""
    try:
        tasks_status[task_id]["status"] = "processing"
        
        # Get API keys
        openai_key = api_keys.get("openai_key")
        google_key = api_keys.get("google_key")
        
        # Validate API keys based on model
        if task.model.startswith(("gpt-", "text-")) and not openai_key:
            raise ValueError("OpenAI API key is required for OpenAI models")
        if task.model.startswith("gemini-") and not google_key:
            raise ValueError("Google API key is required for Gemini models")
        
        # Get or create extractor
        web_extractor = get_or_create_extractor(task.model, openai_key, google_key)
        
        # First, fetch the URL content
        logger.info(f"Task {task_id}: Fetching content from {task.url}")
        fetch_response = await web_extractor.process_query(str(task.url))
        logger.info(f"Task {task_id}: Fetch response: {fetch_response[:100]}...")
        
        # Now process the instructions
        logger.info(f"Task {task_id}: Processing instructions: {task.instructions}")
        
        # Determine if format is specified in the instructions
        format_in_instructions = any(f in task.instructions.lower() for f in ['json', 'csv', 'excel', 'html', 'sql'])
        
        # If format is not in instructions, append it
        instructions = task.instructions
        if not format_in_instructions:
            instructions = f"{instructions} in {task.format} format"
        
        # Execute the instructions
        result = await web_extractor.process_query(instructions)
        
        # Process the result
        data = result
        if isinstance(result, tuple) and len(result) == 2:
            # Result contains data and DataFrame
            content, df = result
            
            if task.format == 'csv':
                data = df.to_csv(index=False)
            elif task.format == 'json':
                data = df.to_json(orient='records', indent=2)
            elif task.format == 'excel':
                # For API, we can't return Excel binary directly, so convert to JSON
                data = df.to_json(orient='records', indent=2)
                task.format = 'json'  # Update format to indicate conversion
        
        # Update task status
        tasks_status[task_id] = {
            "task_id": task_id,
            "status": "completed",
            "url": task.url,
            "format": task.format,
            "data": data,
            "error": None,
            "completed_at": datetime.now()
        }
        
        logger.info(f"Task {task_id} completed successfully")
    except Exception as e:
        logger.error(f"Error processing task {task_id}: {str(e)}", exc_info=True)
        tasks_status[task_id] = {
            "task_id": task_id,
            "status": "failed",
            "url": task.url,
            "format": task.format,
            "data": None,
            "error": str(e),
            "completed_at": datetime.now()
        }

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "CyberScraper API",
        "version": "1.0.0",
        "description": "API for web scraping using CyberScraper 2077's capabilities",
        "endpoints": [
            {"path": "/scrape", "method": "POST", "description": "Submit a scraping task"},
            {"path": "/task/{task_id}", "method": "GET", "description": "Get status and results of a task"}
        ]
    }

@app.post("/scrape", response_model=TaskResponse)
async def create_scraping_task(
    task: ScraperTask, 
    background_tasks: BackgroundTasks, 
    api_keys: Dict[str, str] = Depends(get_api_key)
):
    """
    Create a new scraping task.
    
    - Requires either X-OpenAI-Key or X-Google-Key header depending on the model
    - For OpenAI models (gpt-*), use X-OpenAI-Key
    - For Gemini models (gemini-*), use X-Google-Key
    """
    # Validate API keys
    if task.model.startswith(("gpt-", "text-")) and not api_keys.get("openai_key"):
        raise HTTPException(status_code=400, detail="OpenAI API key is required for OpenAI models")
    if task.model.startswith("gemini-") and not api_keys.get("google_key"):
        raise HTTPException(status_code=400, detail="Google API key is required for Gemini models")
    
    # Generate a unique task ID
    task_id = str(uuid.uuid4())
    
    # Initialize task status
    tasks_status[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "url": task.url,
        "format": task.format,
        "data": None,
        "error": None,
        "completed_at": None
    }
    
    # Schedule the task to run in the background
    background_tasks.add_task(process_scraping_task, task_id, task, api_keys)
    
    return {
        "task_id": task_id,
        "status": "pending",
        "message": f"Task created and processing will begin shortly. Check /task/{task_id} for results."
    }

@app.get("/task/{task_id}", response_model=TaskResult)
async def get_task_status(task_id: str):
    """Get the status and results of a task."""
    if task_id not in tasks_status:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    
    return tasks_status[task_id]

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)