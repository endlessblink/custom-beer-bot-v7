#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WhatsApp Group Summary Bot

This bot connects to a WhatsApp group via Green API,
monitors messages, and periodically generates a summary using OpenAI.
It can be configured to run on a schedule and target specific languages.

Usage:
    python main.py [options]

Options:
    --dry-run              Run in dry-run mode (don't send messages)
    --group-id GROUP_ID    Specify a WhatsApp group ID
    --log-level LEVEL      Set log level (DEBUG, INFO, WARNING, ERROR)
    --help                 Show this help message and exit
"""

import os
import sys
import time
import signal
import argparse
import logging
from dotenv import load_dotenv
from datetime import datetime, timedelta

from config.config_manager import ConfigManager
from green_api.client import GreenAPIClient
from green_api.group_manager import GroupManager
from llm.openai_client import OpenAIClient
from processor.message_processor import MessageProcessor
from scheduler.scheduler import SummaryScheduler
from db.supabase_client import SupabaseClient
from utils.logger import setup_logger

# Global variables
running = True
logger = None


def signal_handler(sig, frame):
    """Handle termination signals"""
    global running
    logger.info("Shutdown signal received")
    running = False


def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="WhatsApp Group Summary Bot")
    
    parser.add_argument("--dry-run", action="store_true", 
                        help="Run in dry-run mode (don't send messages)")
    
    parser.add_argument("--group-id", type=str,
                        help="Specify a WhatsApp group ID")
    
    parser.add_argument("--log-level", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Set log level")
    
    return parser.parse_args()


def validate_environment():
    """Validate environment variables"""
    required_vars = [
        'GREEN_API_ID_INSTANCE',
        'GREEN_API_TOKEN',
        'OPENAI_API_KEY',
        'SUPABASE_URL',
        'SUPABASE_KEY'
    ]
    
    missing = [var for var in required_vars if not os.environ.get(var)]
    
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        return False
    
    return True


def initialize_components(config):
    """Initialize bot components"""
    logger.info("Initializing components...")
    
    # Initialize Green API client
    green_api_client = GreenAPIClient(
        instance_id=config.get('GREEN_API_ID_INSTANCE'),
        instance_token=config.get('GREEN_API_TOKEN'),
        base_url=config.get('GREEN_API_BASE_URL')
    )
    
    # Initialize Group Manager
    group_manager = GroupManager(green_api_client)
    
    # Initialize OpenAI client
    openai_client = OpenAIClient(
        api_key=config.get('OPENAI_API_KEY'),
        model=config.get('OPENAI_MODEL', 'gpt-4'),
        max_tokens=int(config.get('OPENAI_MAX_TOKENS', 2000))
    )
    
    # Initialize message processor
    message_processor = MessageProcessor(
        target_language=config.get('BOT_TARGET_LANGUAGE', 'hebrew')
    )
    
    # Initialize scheduler
    scheduler = SummaryScheduler(
        summary_interval=int(config.get('BOT_SUMMARY_INTERVAL', 24)),
        retry_delay=int(config.get('BOT_RETRY_DELAY', 60)),
        max_retries=int(config.get('BOT_MAX_RETRIES', 3))
    )
    
    # Initialize Supabase client (optional)
    supabase_client = None
    try:
        if config.get('SUPABASE_URL') and config.get('SUPABASE_KEY'):
            logger.info("Initializing Supabase client...")
            supabase_client = SupabaseClient(
                url=config.get('SUPABASE_URL'),
                key=config.get('SUPABASE_KEY')
            )
            logger.info("Supabase client initialized successfully")
        else:
            logger.info("Supabase configuration not found. Database features will be disabled.")
    except Exception as e:
        logger.warning(f"Failed to initialize Supabase client: {str(e)}")
        logger.info("Continuing without database functionality")
    
    return {
        'green_api_client': green_api_client,
        'group_manager': group_manager,
        'openai_client': openai_client,
        'message_processor': message_processor,
        'scheduler': scheduler,
        'supabase_client': supabase_client
    }


def select_group(group_manager, config_manager, args):
    """
    Select a WhatsApp group to monitor.
    If a group ID is provided via command line or environment variable, use that.
    Otherwise, fetch and display available groups for user selection.
    """
    # Check command line argument first
    group_id = args.group_id
    
    # If not provided via command line, check environment variable
    if not group_id:
        group_ids = config_manager.get('WHATSAPP_GROUP_IDS')
        if group_ids:
            # Use the first group ID if multiple are provided
            group_id = group_ids.split(',')[0].strip()
    
    # If still not available, fetch and display available groups
    if not group_id:
        logger.info("No group ID provided. Fetching available groups...")
        
        try:
            groups = group_manager.get_groups()
            
            if not groups:
                logger.error("No groups available. Please join a WhatsApp group first.")
                return None
            
            print("\nAvailable WhatsApp Groups:")
            for i, group in enumerate(groups, 1):
                print(f"{i}. {group['name']} ({group['id']})")
            
            selection = input("\nSelect a group (number): ")
            selection = int(selection.strip())
            
            if selection < 1 or selection > len(groups):
                logger.error("Invalid selection")
                return None
            
            group_name = groups[selection-1]['name']
            group_id = groups[selection-1]['id']
            
            logger.info(f"Selected group: {group_name} (ID: {group_id})")
            
        except Exception as e:
            logger.error(f"Error selecting group: {str(e)}")
            return None
    
    # Validate that the bot can access the group
    try:
        group_data = group_manager.get_group_data(group_id)
        logger.info(f"Connected to group: {group_data['subject']} (ID: {group_id})")
        return group_id
    except Exception as e:
        logger.error(f"Error validating group {group_id}: {str(e)}")
        return None


def schedule_summary_tasks(components, group_id, config_manager):
    """Schedule regular summary tasks"""
    scheduler = components['scheduler']
    green_api_client = components['green_api_client']
    message_processor = components['message_processor']
    openai_client = components['openai_client']
    supabase_client = components['supabase_client']
    
    # Extract configuration
    summary_interval = config_manager.get('BOT_SUMMARY_INTERVAL', 24)
    dry_run = config_manager.get('BOT_DRY_RUN', 'false').lower() == 'true'
    
    # Define the summary task
    def summary_task():
        try:
            logger.info(f"Running scheduled summary for group {group_id}")
            
            # Fetch recent messages
            start_time = datetime.now()
            messages = green_api_client.get_chat_history(group_id)
            
            if not messages:
                logger.info("No messages to summarize")
                return
            
            # Process messages
            processed_messages = message_processor.process_messages(messages)
            
            # Store messages in database
            message_count = supabase_client.store_messages(processed_messages, group_id)
            logger.info(f"Stored {message_count} messages in database")
            
            # Generate summary
            summary = openai_client.generate_summary(processed_messages)
            end_time = datetime.now()
            
            # Store summary in database
            supabase_client.store_summary(
                summary=summary,
                group_id=group_id,
                start_time=start_time,
                end_time=end_time,
                message_count=len(processed_messages),
                model_used=openai_client.model
            )
            logger.info("Summary stored in database")
            
            # Send only summary messages with the is_summary flag
            # SAFETY MEASURE: Force disable all message sending
            message_sending_disabled = True
            
            if message_sending_disabled:
                logger.info("⛔ Message sending is currently disabled for safety.")
                logger.info("Summary not sent to group.")
            elif not dry_run:
                # This code will never execute due to the safety measure above
                green_api_client.send_message(group_id, summary, is_summary=True)
                logger.info(f"Summary sent to group {group_id}")
            else:
                logger.info(f"DRY RUN - Summary would be sent to group {group_id}")
            
            # Display summary in log for debugging purposes
            logger.info(f"Summary content: {summary}")
        
        except Exception as e:
            logger.error(f"Error in summary task: {str(e)}")
    
    # Schedule the task
    scheduler.schedule_summary(summary_task, int(summary_interval))
    
    logger.info(f"Summary task scheduled to run every {summary_interval} hours")


def generate_summary(components, group_id, messages=None):
    """Generate and send a summary of recent messages"""
    green_api_client = components['green_api_client']
    message_processor = components['message_processor']
    openai_client = components['openai_client']
    supabase_client = components['supabase_client']
    
    try:
        # If messages are not provided, fetch them from the chat history
        if messages is None:
            logger.info(f"Fetching messages for group {group_id}")
            messages = green_api_client.get_chat_history(group_id)
        
        if not messages:
            logger.info("No messages to summarize")
            return None
        
        logger.info(f"Processing {len(messages)} messages")
        processed_messages = message_processor.process_messages(messages)
        
        if not processed_messages:
            logger.info("No valid messages to summarize after processing")
            return None
        
        # Store messages in the database
        if supabase_client is not None:
            try:
                message_count = supabase_client.store_messages(processed_messages, group_id)
                logger.info(f"Stored {message_count} messages in database")
            except Exception as e:
                logger.warning(f"Could not store messages in database: {str(e)}")
        else:
            logger.info("Skipping database storage for messages (no database connection)")
        
        # Generate summary
        logger.info("Generating summary...")
        summary = openai_client.generate_summary(processed_messages)
        
        # Store summary in the database
        if supabase_client is not None:
            try:
                supabase_client.store_summary(
                    summary=summary,
                    group_id=group_id,
                    start_time=datetime.now() - timedelta(days=1),
                    end_time=datetime.now(),
                    message_count=len(processed_messages),
                    model_used=openai_client.model
                )
                logger.info("Summary stored in database")
            except Exception as e:
                logger.warning(f"Could not store summary in database: {str(e)}")
        else:
            logger.info("Skipping database storage for summary (no database connection)")
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return None


def main():
    """Main function to run the WhatsApp Group Summary Bot"""
    global logger
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Load environment variables
    load_dotenv(override=True)
    
    # Set up logging
    log_level = args.log_level or os.environ.get('BOT_LOG_LEVEL', 'INFO')
    logger = setup_logger(log_level)
    
    logger.info("Starting WhatsApp Group Summary Bot...")
    
    # Set up signal handlers
    setup_signal_handlers()
    
    # Validate environment
    if not validate_environment():
        sys.exit(1)
    
    # Initialize config manager
    config_manager = ConfigManager()
    
    # Initialize components
    components = initialize_components(config_manager)
    
    # Select group to monitor
    group_id = select_group(components['group_manager'], config_manager, args)
    
    if not group_id:
        logger.error("No valid group selected. Exiting.")
        sys.exit(1)
    
    # Store selected group ID
    config_manager.set('ACTIVE_GROUP_ID', group_id)
    
    # Schedule summary tasks
    schedule_summary_tasks(components, group_id, config_manager)
    
    # Main loop
    logger.info("Bot is running. Press Ctrl+C to stop.")
    
    try:
        while running:
            # Run scheduler cycle
            components['scheduler'].run_pending()
            time.sleep(1)
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)
    
    finally:
        logger.info("Shutting down WhatsApp Group Summary Bot...")
        # Perform cleanup if needed


if __name__ == "__main__":
    main() 