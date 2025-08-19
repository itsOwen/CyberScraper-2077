import requests
import json
import time
import uuid
from typing import Dict, Any, Optional, Union, List
import pandas as pd
from io import StringIO

class CyberScraperMCPClient:
    """Client for interacting with the CyberScraper MCP Server"""
    
    def __init__(self, server_url: str = "http://localhost:8000"):
        """
        Initialize the MCP client.
        
        Args:
            server_url: URL of the CyberScraper MCP server
        """
        self.server_url = server_url.rstrip('/')
        self.mcp_endpoint = f"{self.server_url}/mcp"
    
    def _send_mcp_request(self, operation: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a request to the MCP server.
        
        Args:
            operation: Operation to perform
            data: Request data
            
        Returns:
            Dict containing the server response
        """
        # Add operation to data
        data["operation"] = operation
        
        # Create request payload
        request_id = str(uuid.uuid4())
        payload = {
            "id": request_id,
            "data": data
        }
        
        # Send request
        response = requests.post(self.mcp_endpoint, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"Error: {response.status_code} - {response.text}")
        
        # Parse response
        response_data = response.json()
        
        # Check for errors
        if response_data.get("error"):
            raise Exception(f"Server error: {response_data['error']}")
        
        return response_data["data"]
    
    def scrape(self, 
              url: str, 
              instructions: str,
              model: str = "gpt-4o-mini",
              format: str = "json",
              openai_key: Optional[str] = None,
              google_key: Optional[str] = None) -> str:
        """
        Submit a scraping task.
        
        Args:
            url: URL to scrape
            instructions: Instructions for what data to extract
            model: Model to use (default: gpt-4o-mini)
            format: Output format (default: json)
            openai_key: OpenAI API key (required for OpenAI models)
            google_key: Google API key (required for Gemini models)
            
        Returns:
            Task ID for tracking the scraping task
        """
        # Validate API keys based on model
        if model.startswith(("gpt-", "text-")) and not openai_key:
            raise ValueError("OpenAI API key is required for OpenAI models")
        if model.startswith("gemini-") and not google_key:
            raise ValueError("Google API key is required for Gemini models")
        
        # Prepare request data
        data = {
            "url": url,
            "instructions": instructions,
            "model": model,
            "format": format
        }
        
        # Add API keys if provided
        if openai_key:
            data["openai_key"] = openai_key
        if google_key:
            data["google_key"] = google_key
        
        # Send request
        response = self._send_mcp_request("scrape", data)
        
        # Return task ID
        return response["task_id"]
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the status of a scraping task.
        
        Args:
            task_id: Task ID to check
            
        Returns:
            Dict containing task status and data (if available)
        """
        # Prepare request data
        data = {
            "task_id": task_id
        }
        
        # Send request
        return self._send_mcp_request("get_task_status", data)
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the MCP server.
        
        Returns:
            Dict containing server health status
        """
        return self._send_mcp_request("health_check", {})
    
    def wait_for_result(self, 
                      task_id: str, 
                      polling_interval: int = 5, 
                      max_polls: int = 60) -> Dict[str, Any]:
        """
        Wait for a scraping task to complete.
        
        Args:
            task_id: Task ID to wait for
            polling_interval: Seconds to wait between status checks
            max_polls: Maximum number of status checks
            
        Returns:
            Dict containing task results
        """
        polls = 0
        
        while polls < max_polls:
            # Get task status
            status = self.get_task_status(task_id)
            
            # Check if task is complete
            if status["status"] in ("completed", "failed"):
                return status
            
            # Wait for next poll
            time.sleep(polling_interval)
            polls += 1
        
        raise TimeoutError(f"Task {task_id} did not complete within the timeout period")
    
    def scrape_and_wait(self, 
                      url: str, 
                      instructions: str,
                      model: str = "gpt-4o-mini",
                      format: str = "json",
                      openai_key: Optional[str] = None,
                      google_key: Optional[str] = None,
                      polling_interval: int = 5, 
                      max_polls: int = 60) -> Dict[str, Any]:
        """
        Submit a scraping task and wait for it to complete.
        
        Args:
            url: URL to scrape
            instructions: Instructions for what data to extract
            model: Model to use (default: gpt-4o-mini)
            format: Output format (default: json)
            openai_key: OpenAI API key (required for OpenAI models)
            google_key: Google API key (required for Gemini models)
            polling_interval: Seconds to wait between status checks
            max_polls: Maximum number of status checks
            
        Returns:
            Dict containing task results
        """
        # Submit task
        task_id = self.scrape(url, instructions, model, format, openai_key, google_key)
        
        # Wait for result
        return self.wait_for_result(task_id, polling_interval, max_polls)
    
    def scrape_to_df(self, 
                   url: str, 
                   instructions: str,
                   model: str = "gpt-4o-mini",
                   openai_key: Optional[str] = None,
                   google_key: Optional[str] = None,
                   polling_interval: int = 5, 
                   max_polls: int = 60) -> pd.DataFrame:
        """
        Submit a scraping task and convert the result to a pandas DataFrame.
        
        Args:
            url: URL to scrape
            instructions: Instructions for what data to extract
            model: Model to use (default: gpt-4o-mini)
            openai_key: OpenAI API key (required for OpenAI models)
            google_key: Google API key (required for Gemini models)
            polling_interval: Seconds to wait between status checks
            max_polls: Maximum number of status checks
            
        Returns:
            pandas DataFrame containing the scraped data
        """
        # Always use JSON format for DataFrame conversion
        result = self.scrape_and_wait(
            url, 
            instructions, 
            model, 
            "json", 
            openai_key, 
            google_key, 
            polling_interval, 
            max_polls
        )
        
        # Check if task completed successfully
        if result["status"] != "completed":
            raise Exception(f"Task failed: {result.get('error', 'Unknown error')}")
        
        # Convert to DataFrame
        data = result["data"]
        
        # Handle string data
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                # Try to parse as CSV if JSON parsing fails
                try:
                    return pd.read_csv(StringIO(data))
                except Exception as e:
                    raise ValueError(f"Failed to parse data: {str(e)}")
        
        # Convert to DataFrame
        return pd.DataFrame(data)
    
    def save_result(self, 
                  result: Dict[str, Any], 
                  output_file: Optional[str] = None) -> str:
        """
        Save the scraped data to a file.
        
        Args:
            result: Task result from get_task_status or wait_for_result
            output_file: Output file path (optional)
            
        Returns:
            Path to the saved file
        """
        if result["status"] != "completed":
            raise ValueError("Cannot save result: task did not complete successfully")
        
        data = result["data"]
        format_type = result["format"]
        
        # Generate default filename if not provided
        if not output_file:
            url_parts = str(result["url"]).split("/")
            domain = url_parts[2] if len(url_parts) > 2 else "scraped"
            output_file = f"{domain}_data.{format_type}"
        
        # Save file based on format
        with open(output_file, "w", encoding="utf-8") as f:
            if isinstance(data, str):
                f.write(data)
            else:
                if format_type == "json":
                    json.dump(data, f, indent=2)
                else:
                    f.write(str(data))
        
        return output_file
