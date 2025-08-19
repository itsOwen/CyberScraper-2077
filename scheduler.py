import json
import os
import time
import logging
import asyncio
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

# Import necessary components from CyberScraper
from src.web_extractor import WebExtractor
from src.scrapers.playwright_scraper import ScraperConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cyberscraper_scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CyberScraperScheduler")

class TaskScheduler:
    """
    Scheduler for CyberScraper tasks defined in a master JSON file.
    Executes web scraping tasks at specified times and saves the results.
    """
    
    def __init__(self, tasks_file: str = "tasks.json", openai_api_key: str = None, google_api_key: str = None):
        """
        Initialize the TaskScheduler.
        
        Args:
            tasks_file: Path to the JSON file containing task definitions
            openai_api_key: OpenAI API key (overrides environment variable)
            google_api_key: Google API key for Gemini models (overrides environment variable)
        """
        self.tasks_file = tasks_file
        self.tasks = []
        self.web_extractors = {}  # Cache for web extractors by model name
        
        # Set API keys if provided
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
            logger.info("OpenAI API key set from parameter")
        
        if google_api_key:
            os.environ["GOOGLE_API_KEY"] = google_api_key
            logger.info("Google API key set from parameter")
        
        self.load_tasks()
        logger.info(f"TaskScheduler initialized with tasks file: {self.tasks_file}")
    
    def load_tasks(self) -> None:
        """Load tasks from the tasks file."""
        try:
            if os.path.exists(self.tasks_file):
                with open(self.tasks_file, 'r') as f:
                    self.tasks = json.load(f)
                logger.info(f"Loaded {len(self.tasks)} tasks from {self.tasks_file}")
            else:
                logger.warning(f"Tasks file {self.tasks_file} not found. Creating empty tasks list.")
                self.tasks = []
        except json.JSONDecodeError:
            logger.error(f"Error parsing tasks file {self.tasks_file}. Using empty tasks list.")
            self.tasks = []
    
    def save_tasks(self) -> None:
        """Save tasks to the tasks file."""
        with open(self.tasks_file, 'w') as f:
            json.dump(self.tasks, f, indent=2)
        logger.info(f"Saved {len(self.tasks)} tasks to {self.tasks_file}")
    
    def _get_extractor(self, model_name: str) -> WebExtractor:
        """
        Get or create a WebExtractor for the specified model.
        
        Args:
            model_name: Name of the model to use
            
        Returns:
            WebExtractor: The extractor for the model
        """
        if model_name not in self.web_extractors:
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
            self.web_extractors[model_name] = WebExtractor(model_name=model_name, scraper_config=scraper_config)
        
        return self.web_extractors[model_name]
    
    async def execute_task(self, task: Dict[str, Any]) -> None:
        """
        Execute a single scraping task.
        
        Args:
            task: Task to execute
        """
        task_id = task['id']
        url = task['url']
        instructions = task['instructions']
        output_path = task['output_path']
        output_filename = task['output_filename']
        format_type = task.get('format', 'csv').lower()
        model = task.get('model', 'gpt-4o-mini')
        enabled = task.get('enabled', True)
        
        if not enabled:
            logger.info(f"Skipping disabled task: {task_id}")
            return
        
        logger.info(f"Executing task: {task_id}")
        logger.info(f"URL: {url}")
        logger.info(f"Instructions: {instructions}")
        
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_path, exist_ok=True)
            
            # Get the web extractor for this model
            web_extractor = self._get_extractor(model)
            
            # First, fetch the URL content
            logger.info(f"Fetching content from {url}")
            fetch_response = await web_extractor.process_query(url)
            logger.info(f"Fetch response: {fetch_response}")
            
            # Now process the instructions
            logger.info(f"Processing instructions: {instructions}")
            
            # Determine if format is specified in the instructions
            format_in_instructions = any(f in instructions.lower() for f in ['json', 'csv', 'excel', 'html', 'sql'])
            
            # If format is not in instructions, append it
            if not format_in_instructions:
                instructions = f"{instructions} in {format_type} format"
            
            # Execute the instructions
            result = await web_extractor.process_query(instructions)
            
            # Process timestamp placeholders in output_filename
            timestamp = datetime.now()
            processed_filename = output_filename
            
            # Replace timestamp placeholders
            if '{timestamp}' in processed_filename:
                processed_filename = processed_filename.replace('{timestamp}', timestamp.strftime('%Y%m%d_%H%M%S'))
            if '{date}' in processed_filename:
                processed_filename = processed_filename.replace('{date}', timestamp.strftime('%Y%m%d'))
            if '{time}' in processed_filename:
                processed_filename = processed_filename.replace('{time}', timestamp.strftime('%H%M%S'))
            if '{year}' in processed_filename:
                processed_filename = processed_filename.replace('{year}', timestamp.strftime('%Y'))
            if '{month}' in processed_filename:
                processed_filename = processed_filename.replace('{month}', timestamp.strftime('%m'))
            if '{day}' in processed_filename:
                processed_filename = processed_filename.replace('{day}', timestamp.strftime('%d'))
            
            # Handle different output formats
            full_output_path = os.path.join(output_path, processed_filename)
            
            if isinstance(result, tuple) and len(result) == 2:
                # Result contains data and DataFrame
                data, df = result
                
                if format_type == 'csv':
                    df.to_csv(full_output_path, index=False)
                    logger.info(f"Saved CSV to {full_output_path}")
                elif format_type == 'excel':
                    df.to_excel(full_output_path, index=False)
                    logger.info(f"Saved Excel to {full_output_path}")
                elif format_type == 'json':
                    df.to_json(full_output_path, orient='records', lines=False, indent=2)
                    logger.info(f"Saved JSON to {full_output_path}")
                else:
                    # Default to CSV if format is not recognized
                    df.to_csv(full_output_path, index=False)
                    logger.info(f"Saved CSV to {full_output_path} (default format)")
            else:
                # Just save the raw result
                with open(full_output_path, 'w', encoding='utf-8') as f:
                    f.write(str(result))
                logger.info(f"Saved raw result to {full_output_path}")
            
            # Update task's last execution time
            for i, t in enumerate(self.tasks):
                if t['id'] == task_id:
                    self.tasks[i]['last_executed'] = datetime.now().isoformat()
                    break
            
            self.save_tasks()
            logger.info(f"Task {task_id} executed successfully")
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {str(e)}", exc_info=True)
    
    def _should_execute_now(self, schedule_time: str) -> bool:
        """
        Check if a task should be executed now based on its schedule time.
        
        Args:
            schedule_time: Time when the task should be executed (HH:MM format)
            
        Returns:
            bool: True if the task should be executed now, False otherwise
        """
        now = datetime.now()
        # Parse the schedule time (HH:MM)
        try:
            hour, minute = map(int, schedule_time.split(':'))
            scheduled_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # Check if current time is within 1 minute of the scheduled time
            time_diff = abs((now - scheduled_time).total_seconds())
            return time_diff <= 60
        except ValueError:
            logger.error(f"Invalid schedule time format: {schedule_time}. Expected HH:MM format.")
            return False
    
    async def check_and_execute_tasks(self) -> None:
        """Check for tasks that need to be executed and execute them."""
        logger.info("Checking for tasks to execute...")
        
        for task in self.tasks:
            schedule_time = task.get('schedule_time')
            if not schedule_time:
                continue
            
            if self._should_execute_now(schedule_time):
                logger.info(f"Task {task['id']} is scheduled to run now")
                await self.execute_task(task)
    
    async def run(self) -> None:
        """Run the scheduler in an infinite loop."""
        logger.info("Starting scheduler...")
        
        while True:
            await self.check_and_execute_tasks()
            await asyncio.sleep(60)  # Check every minute

    async def run_once(self) -> None:
        """Run the scheduler once, executing all enabled tasks regardless of schedule."""
        logger.info("Running scheduler once, executing all enabled tasks...")
        
        for task in self.tasks:
            if task.get('enabled', True):
                logger.info(f"Executing task {task['id']} (run_once mode)")
                await self.execute_task(task)
        
        logger.info("Scheduler run completed. All enabled tasks have been executed.")

    async def execute_task_by_id(self, task_id: str) -> None:
        """
        Execute a task by its ID, regardless of schedule.
        
        Args:
            task_id: ID of the task to execute
        """
        for task in self.tasks:
            if task['id'] == task_id:
                logger.info(f"Executing task {task_id} on demand")
                await self.execute_task(task)
                return
        
        logger.error(f"No task found with ID: {task_id}")

# Entry point for running the scheduler
async def main(openai_api_key=None, google_api_key=None, run_mode="continuous", task_id=None):
    """
    Main entry point for the scheduler.
    
    Args:
        openai_api_key: OpenAI API key
        google_api_key: Google API key
        run_mode: Mode to run the scheduler in ("continuous", "once", "task")
        task_id: ID of the task to execute (only used in "task" mode)
    """
    scheduler = TaskScheduler(
        openai_api_key=openai_api_key, 
        google_api_key=google_api_key
    )
    
    if run_mode == "continuous":
        await scheduler.run()
    elif run_mode == "once":
        await scheduler.run_once()
    elif run_mode == "task" and task_id:
        await scheduler.execute_task_by_id(task_id)
    else:
        logger.error(f"Invalid run_mode: {run_mode}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="CyberScraper Task Scheduler")
    parser.add_argument("--openai-key", help="OpenAI API key")
    parser.add_argument("--google-key", help="Google API key for Gemini models")
    parser.add_argument("--mode", choices=["continuous", "once", "task"], default="continuous",
                        help="Run mode: continuous (run until stopped), once (run all enabled tasks immediately), or task (run a specific task)")
    parser.add_argument("--task-id", help="Task ID to execute (only used with --mode=task)")
    parser.add_argument("--tasks-file", default="tasks.json", help="Path to tasks JSON file")
    
    args = parser.parse_args()
    
    # Run the scheduler with the provided arguments
    asyncio.run(main(
        openai_api_key=args.openai_key,
        google_api_key=args.google_key,
        run_mode=args.mode,
        task_id=args.task_id
    ))