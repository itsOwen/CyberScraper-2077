import requests
import json
import time
import argparse
import sys
import pandas as pd
from typing import Optional

def scrape_with_api(
    url: str, 
    instructions: str, 
    api_url: str,
    openai_key: Optional[str] = None,
    google_key: Optional[str] = None,
    format: str = "json",
    model: str = "gpt-4o-mini",
    polling_interval: int = 5,
    max_polls: int = 60
) -> dict:
    """
    Send a scraping request to the CyberScraper API and poll for results.
    
    Args:
        url: URL to scrape
        instructions: Instructions for what data to extract
        api_url: Base URL of the CyberScraper API
        openai_key: OpenAI API key (required for OpenAI models)
        google_key: Google API key (required for Gemini models)
        format: Output format (json, csv, excel, html, sql)
        model: Model to use (gpt-4o-mini, gpt-3.5-turbo, gemini-pro, etc.)
        polling_interval: Seconds to wait between status checks
        max_polls: Maximum number of status checks before giving up
        
    Returns:
        Dict containing the task results
    """
    # Prepare headers based on model type
    headers = {"Content-Type": "application/json"}
    
    if model.startswith(("gpt-", "text-")):
        if not openai_key:
            raise ValueError("OpenAI API key is required for OpenAI models")
        headers["X-OpenAI-Key"] = openai_key
    elif model.startswith("gemini-"):
        if not google_key:
            raise ValueError("Google API key is required for Gemini models")
        headers["X-Google-Key"] = google_key
    
    # Prepare request payload
    payload = {
        "url": url,
        "instructions": instructions,
        "format": format,
        "model": model
    }
    
    # Submit scraping task
    print(f"Submitting scraping task for {url}...")
    response = requests.post(f"{api_url}/scrape", headers=headers, json=payload)
    
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return {"status": "error", "message": response.text}
    
    task_data = response.json()
    task_id = task_data["task_id"]
    print(f"Task submitted successfully. Task ID: {task_id}")
    
    # Poll for results
    polls = 0
    while polls < max_polls:
        time.sleep(polling_interval)
        
        print(f"Checking task status ({polls+1}/{max_polls})...")
        status_response = requests.get(f"{api_url}/task/{task_id}")
        
        if status_response.status_code != 200:
            print(f"Error checking status: {status_response.status_code} - {status_response.text}")
            continue
        
        result = status_response.json()
        
        if result["status"] == "completed":
            print("Task completed successfully!")
            return result
        elif result["status"] == "failed":
            print(f"Task failed: {result['error']}")
            return result
        
        polls += 1
        print(f"Task still processing. Status: {result['status']}")
    
    print("Maximum polling attempts reached. The task may still be processing.")
    return {"status": "timeout", "message": "Maximum polling attempts reached"}

def save_result(result: dict, output_file: Optional[str] = None) -> None:
    """
    Save the API result to a file based on the format.
    
    Args:
        result: The API result dictionary
        output_file: Output filename (optional)
    """
    if result["status"] != "completed":
        print("No data to save.")
        return
    
    data = result["data"]
    format = result["format"]
    
    if not output_file:
        url_parts = result["url"].split("/")
        domain = url_parts[2] if len(url_parts) > 2 else "scraped"
        output_file = f"{domain}_data.{format}"
    
    print(f"Saving data to {output_file}...")
    
    if format == "json":
        # If data is already a string, parse it to ensure it's valid JSON
        if isinstance(data, str):
            try:
                json_data = json.loads(data)
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(json_data, f, indent=2)
            except json.JSONDecodeError:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(data)
        else:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
    
    elif format == "csv":
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(data)
    
    else:
        # For other formats, just write the data as is
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(str(data))
    
    print(f"Data saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="CyberScraper API Client")
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument("instructions", help="Instructions for what data to extract")
    parser.add_argument("--api-url", default="http://localhost:8000", help="CyberScraper API URL")
    parser.add_argument("--openai-key", help="OpenAI API key")
    parser.add_argument("--google-key", help="Google API key for Gemini models")
    parser.add_argument("--format", default="json", choices=["json", "csv", "excel", "html", "sql"],
                       help="Output format (default: json)")
    parser.add_argument("--model", default="gpt-4o-mini", 
                       help="Model to use (default: gpt-4o-mini)")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--polling-interval", type=int, default=5,
                       help="Seconds between status checks (default: 5)")
    parser.add_argument("--max-polls", type=int, default=60,
                       help="Maximum number of status checks (default: 60)")
    
    args = parser.parse_args()
    
    try:
        result = scrape_with_api(
            url=args.url,
            instructions=args.instructions,
            api_url=args.api_url,
            openai_key=args.openai_key,
            google_key=args.google_key,
            format=args.format,
            model=args.model,
            polling_interval=args.polling_interval,
            max_polls=args.max_polls
        )
        
        if result["status"] == "completed":
            save_result(result, args.output)
            
            # Print a preview of the data
            print("\nData Preview:")
            if args.format == "json":
                data = result["data"]
                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except json.JSONDecodeError:
                        pass
                print(json.dumps(data[:5] if isinstance(data, list) else data, indent=2))
            else:
                print(result["data"][:500] + "..." if len(result["data"]) > 500 else result["data"])
        else:
            print(f"Task did not complete successfully: {result}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())