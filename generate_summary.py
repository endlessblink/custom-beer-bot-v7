#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Manual Summary Generator

This script generates a summary of recent WhatsApp group messages on demand.
It can either display the summary in the console or send it to the group.

Usage:
    python generate_summary.py [options]

Options:
    --group-id GROUP_ID  Specify a WhatsApp group ID
    --days DAYS          Number of days of messages to summarize (default: 1)
    --send               Send the summary to the group
    --help               Show this help message and exit
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json

from config.config_manager import ConfigManager
from green_api.client import GreenAPIClient
from green_api.group_manager import GroupManager
from llm.openai_client import OpenAIClient
from processor.message_processor import MessageProcessor
from db.supabase_client import SupabaseClient
from utils.logger import setup_logger


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="WhatsApp Group Manual Summary Generator")
    
    parser.add_argument("--group-id", type=str,
                        help="Specify a WhatsApp group ID")
    
    parser.add_argument("--days", type=int, default=1,
                        help="Number of days of messages to summarize (default: 1)")
    
    parser.add_argument("--send", action="store_true",
                        help="Send the summary to the group")
    
    return parser.parse_args()


def initialize_components(config):
    """Initialize bot components"""
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
        model=config.get('OPENAI_MODEL', 'gpt-4o-mini'),
        max_tokens=int(config.get('OPENAI_MAX_TOKENS', 2000))
    )
    
    # Initialize message processor
    message_processor = MessageProcessor(
        target_language=config.get('BOT_TARGET_LANGUAGE', 'hebrew')
    )
    
    # Initialize Supabase client (optional)
    try:
        supabase_client = SupabaseClient(
            url=config.get('SUPABASE_URL'),
            key=config.get('SUPABASE_KEY')
        )
    except Exception as e:
        logger.warning(f"Could not initialize Supabase client: {str(e)}")
        supabase_client = None
    
    return {
        'green_api_client': green_api_client,
        'group_manager': group_manager,
        'openai_client': openai_client,
        'message_processor': message_processor,
        'supabase_client': supabase_client
    }


def select_group(group_manager, config_manager, args):
    """Select a WhatsApp group"""
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


def generate_summary(components, group_id, days=1):
    """Generate a summary of recent messages"""
    green_api_client = components['green_api_client']
    message_processor = components['message_processor']
    openai_client = components['openai_client']
    supabase_client = components['supabase_client']
    
    try:
        # Fetch recent messages
        logger.info(f"Fetching messages for group {group_id}")
        messages = green_api_client.get_chat_history(group_id)
        
        if not messages:
            logger.info("No messages to summarize")
            return "אין הודעות לסיכום."
        
        # Print some debug info about the messages
        print(f"\nFound {len(messages)} raw messages in the group")
        if len(messages) > 0:
            print("First message sample:")
            print(json.dumps(messages[0], indent=2, ensure_ascii=False)[:500] + "...")
        
        # Process messages
        logger.info(f"Processing {len(messages)} messages")
        processed_messages = message_processor.process_messages(messages)
        
        if not processed_messages:
            logger.info("No valid messages to summarize after processing")
            print("\nMessage processing filter details:")
            print("- The processor filters out commands (messages starting with /, !, .)")
            print("- It also filters out empty messages or unsupported message types")
            print("- Check if recent messages in the group are valid text messages")
            return "אין הודעות תקפות לסיכום."
        
        # Print some info about processed messages
        print(f"\nAfter processing: {len(processed_messages)} valid messages")
        if len(processed_messages) > 0:
            print("First processed message sample:")
            print(json.dumps(processed_messages[0], indent=2, ensure_ascii=False))
        
        # Try to store messages in the database if available
        if supabase_client:
            try:
                start_time = datetime.now() - timedelta(days=days)
                message_count = supabase_client.store_messages(processed_messages, group_id)
                logger.info(f"Stored {message_count} messages in database")
            except Exception as e:
                logger.warning(f"Could not store messages in database: {str(e)}")
                print(f"\nDatabase warning: {str(e)}")
        else:
            logger.info("Skipping database storage (no database connection)")
            print("\nDatabase storage: DISABLED (no connection)")
        
        # Generate summary
        logger.info("Generating summary...")
        summary = openai_client.generate_summary(processed_messages)
        
        # Try to store the summary in the database if available
        if supabase_client:
            try:
                end_time = datetime.now()
                start_time = end_time - timedelta(days=days)
                supabase_client.store_summary(
                    summary=summary,
                    group_id=group_id,
                    start_time=start_time,
                    end_time=end_time,
                    message_count=len(processed_messages),
                    model_used=openai_client.model
                )
                logger.info("Summary stored in database")
            except Exception as e:
                logger.warning(f"Could not store summary in database: {str(e)}")
                print(f"\nDatabase warning: {str(e)}")
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return f"שגיאה בזמן יצירת הסיכום: {str(e)}"


def main():
    """Main function"""
    global logger
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Load environment variables
    load_dotenv(override=True)
    
    # Set up logging
    logger = setup_logger("DEBUG")
    
    logger.info("Starting WhatsApp Group Manual Summary Generator...")
    
    # Initialize config manager
    config_manager = ConfigManager()
    
    # Initialize components
    components = initialize_components(config_manager)
    
    # Select group to monitor
    group_id = select_group(components['group_manager'], config_manager, args)
    
    if not group_id:
        logger.error("No valid group selected. Exiting.")
        sys.exit(1)
    
    # Generate summary
    summary = generate_summary(components, group_id, days=args.days)
    
    # Display the summary
    print("\n" + "="*50)
    print("SUMMARY:")
    print("="*50)
    print(summary)
    print("="*50)
    
    # Check if user wants to send the summary to the group
    should_send = args.send
    
    # If not specified via command line, ask interactively
    if not args.send:
        send_choice = input("\nשלח את הסיכום לקבוצה? (כ/ל): ").strip().lower()
        should_send = send_choice in ['כ', 'כן', 'y', 'yes']
    
    if should_send:
        # SAFETY MEASURE: Force disable all message sending
        message_sending_disabled = True
        
        # Previous settings (now just for information)
        config_disabled = config_manager.get('BOT_MESSAGE_SENDING_DISABLED', 'false').lower() == 'true'
        dry_run = config_manager.get('BOT_DRY_RUN', 'true').lower() == 'true'
        
        if message_sending_disabled:
            logger.info("Message sending is currently disabled for safety")
            print("\n⛔ שליחת הודעות מושבתת כעת בתור אמצעי בטיחות.")
            print("הסיכום לא יישלח לקבוצה.")
        elif config_disabled:
            # This will never execute due to the safety measure above
            logger.info("Message sending is disabled in configuration")
            print("\n⛔ שליחת הודעות מושבתת בקובץ ההגדרות. עדכן את BOT_MESSAGE_SENDING_DISABLED ל-false כדי לאפשר שליחה.")
        elif dry_run:
            # This will never execute due to the safety measure above
            logger.info(f"DRY RUN - Summary would be sent to group {group_id}")
            print("\n⚠️ מצב DRY RUN מופעל. הסיכום לא נשלח לקבוצה. עדכן את BOT_DRY_RUN ל-false כדי לאפשר שליחה.")
        else:
            # This will never execute due to the safety measure above
            # Send the summary with the is_summary flag
            green_api_client = components['green_api_client']
            response = green_api_client.send_message(group_id, summary, is_summary=True)
            
            if 'idMessage' in response and not response['idMessage'].startswith(('DISABLED', 'NON-SUMMARY')):
                logger.info(f"Summary sent to group {group_id}")
                print("\n✅ הסיכום נשלח לקבוצה בהצלחה.")
            else:
                logger.warning(f"Failed to send summary. Response: {response}")
                print(f"\n❌ נכשל בשליחת הסיכום: {response.get('message', 'Unknown error')}")
    else:
        print("\nℹ️ הסיכום לא נשלח לקבוצה. הוא מוצג רק כאן בקונסולה.")


if __name__ == "__main__":
    main() 