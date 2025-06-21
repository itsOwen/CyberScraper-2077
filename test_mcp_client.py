# test_mcp_client.py
import argparse
import sys
from cyberscraper_mcp_client import CyberScraperMCPClient

def run_test(url, instructions, server_url, openai_key=None, google_key=None):
    print(f"Connecting to MCP server at {server_url}...")
    client = CyberScraperMCPClient(server_url)
    
    # Test health check first
    try:
        health = client.health_check()
        print(f"Server health: {health['status']}")
        print(f"Server timestamp: {health.get('timestamp', 'N/A')}")
        print("Health check passed!")
    except Exception as e:
        print(f"Health check failed: {str(e)}")
        return
    
    # Now test a scraping operation
    try:
        print("\nTesting scraping operation...")
        print(f"Submitting task to scrape {url}")
        print(f"Instructions: {instructions}")
        
        # Determine which model to use based on provided keys
        if openai_key:
            model = "gpt-4o-mini"
            key_type = "OpenAI"
        elif google_key:
            model = "gemini-pro"
            key_type = "Google"
        else:
            print("Error: You must provide either an OpenAI API key or a Google API key")
            return
        
        print(f"Using {key_type} model: {model}")
        
        # Start a scraping task
        task_id = client.scrape(
            url=url,
            instructions=instructions,
            model=model,
            format="json",
            openai_key=openai_key,
            google_key=google_key
        )
        
        print(f"Task submitted successfully. Task ID: {task_id}")
        print("Waiting for results (this may take a minute)...")
        
        # Wait for the task to complete
        result = client.wait_for_result(task_id)
        
        print(f"\nTask status: {result['status']}")
        
        if result['status'] == 'completed':
            print("\nScraped data:")
            print(result['data'])
        else:
            print(f"Task failed: {result.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"Scraping test failed: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Test MCP Client")
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument("instructions", help="Instructions for what data to extract")
    parser.add_argument("--server", default="http://localhost:8000", help="MCP server URL")
    parser.add_argument("--openai-key", help="OpenAI API key")
    parser.add_argument("--google-key", help="Google API key")
    
    args = parser.parse_args()
    
    if not args.openai_key and not args.google_key:
        print("Error: You must provide either --openai-key or --google-key")
        return 1
    
    run_test(args.url, args.instructions, args.server, args.openai_key, args.google_key)
    return 0

if __name__ == "__main__":
    sys.exit(main())