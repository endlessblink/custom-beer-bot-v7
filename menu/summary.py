#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Summary Generation Module

This module handles summary generation and sending for the menu interface.
"""

import logging
import time
from datetime import datetime, timedelta
from utils.menu.core_menu import show_menu, display_error_and_continue, confirm_action

logger = logging.getLogger("whatsapp_bot")

def select_days():
    """
    Allow user to select a time period for the summary
    
    Returns:
        int: Number of days to include in the summary, or 0 if canceled
    """
    try:
        options = [
            {'key': '1', 'text': 'Last 24 hours'},
            {'key': '2', 'text': 'Last 3 days'},
            {'key': '3', 'text': 'Last week'},
            {'key': '4', 'text': 'Last month'},
            {'key': '5', 'text': 'Custom period'},
            {'key': 'c', 'text': 'Cancel'}
        ]
        
        choice = show_menu("Select time period", options)
        
        if choice.lower() == 'c':
            logger.info("User canceled time period selection")
            return 0
        
        days_mapping = {
            '1': 1,     # Last 24 hours
            '2': 3,     # Last 3 days
            '3': 7,     # Last week
            '4': 30,    # Last month
        }
        
        if choice in days_mapping:
            days = days_mapping[choice]
            logger.info(f"Selected time period: {days} days")
            return days
            
        elif choice == '5':  # Custom period
            try:
                print("\nEnter custom time period in days (1-90):")
                custom_days = int(input("Number of days: ").strip())
                
                if custom_days < 1 or custom_days > 90:
                    logger.warning(f"Invalid custom period: {custom_days} days")
                    display_error_and_continue("Custom period must be between 1 and 90 days")
                    return 0
                    
                logger.info(f"Selected custom time period: {custom_days} days")
                return custom_days
                
            except ValueError:
                logger.warning("Invalid input for custom time period")
                display_error_and_continue("Please enter a valid number")
                return 0
        else:
            logger.warning(f"Invalid time period selection: {choice}")
            display_error_and_continue("Invalid selection")
            return 0
            
    except Exception as e:
        logger.error(f"Error selecting time period: {str(e)}", exc_info=True)
        display_error_and_continue(f"Error: {str(e)}")
        return 0

def filter_messages_by_date(messages, days):
    """
    Filter messages based on a specified number of days
    
    Args:
        messages (list): List of messages to filter
        days (int): Number of days to include
        
    Returns:
        list: Filtered list of messages
    """
    if not messages or not isinstance(messages, list) or days <= 0:
        return []
        
    try:
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days)
        logger.info(f"Filtering messages since {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        filtered_messages = []
        for message in messages:
            try:
                # Extract timestamp from message
                timestamp_str = message.get('timestamp')
                if not timestamp_str:
                    continue
                    
                # Parse timestamp
                if isinstance(timestamp_str, str):
                    message_date = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    # Assume it's already a datetime
                    message_date = timestamp_str
                    
                # Compare with cutoff
                if message_date >= cutoff_date:
                    filtered_messages.append(message)
                    
            except Exception as e:
                logger.warning(f"Error parsing message timestamp: {str(e)}")
                continue
                
        logger.info(f"Filtered {len(filtered_messages)} messages out of {len(messages)}")
        return filtered_messages
        
    except Exception as e:
        logger.error(f"Error filtering messages by date: {str(e)}", exc_info=True)
        return []

def generate_summary(components, group_id=None, days=None, use_api=True):
    """
    Generate a summary for a group's messages
    
    Args:
        components (dict): Dictionary of initialized components
        group_id (str): ID of the WhatsApp group
        days (int): Number of days to include in the summary
        use_api (bool): Whether to use API to fetch fresh messages
        
    Returns:
        str: Generated summary text, or None if failed
    """
    if not components or not group_id or not days or days <= 0:
        logger.error(f"Invalid parameters for generate_summary: group_id={group_id}, days={days}")
        return None
        
    try:
        # Validate components
        message_processor = components.get('message_processor')
        openai_client = components.get('openai_client')
        group_manager = components.get('group_manager')
        supabase = components.get('supabase_client')
        
        if not message_processor or not openai_client or not group_manager or not supabase:
            logger.error("Missing required components for summary generation")
            return None
            
        # Collect messages
        messages = []
        
        # Option 1: Fetch fresh messages from API
        if use_api:
            logger.info(f"Fetching messages from API for group {group_id}")
            try:
                api_messages = group_manager.get_chat_history(group_id, days)
                if api_messages and isinstance(api_messages, list):
                    messages = api_messages
                    logger.info(f"Fetched {len(messages)} messages from API")
                else:
                    logger.warning("No messages fetched from API")
                    
            except Exception as e:
                logger.error(f"Error fetching messages from API: {str(e)}", exc_info=True)
                
        # Option 2: Fetch messages from database
        if not use_api or not messages:
            logger.info(f"Fetching messages from database for group {group_id}")
            try:
                # נסה מספר גישות שונות לפניה אל ה-API
                try:
                    # גישה 1 - הדרך החדשה
                    result = supabase.client.table('messages').select('*').eq('group_id', group_id).execute()
                except Exception as e1:
                    logger.warning(f"First access method failed: {str(e1)}")
                    try:
                        # גישה 2 - הדרך הישנה
                        result = supabase.table('messages').select('*').eq('group_id', group_id).execute()
                    except Exception as e2:
                        logger.warning(f"Second access method failed: {str(e2)}")
                        # גישה 3 - פניה ישירה
                        result = supabase.client.from_('messages').select('*').eq('group_id', group_id).execute()
                
                if not result or not hasattr(result, 'data') or not result.data:
                    logger.warning(f"No messages found in database for group {group_id}")
                    return None
                    
                messages = result.data
                logger.info(f"Found {len(messages)} messages in database")
                
            except Exception as e:
                logger.error(f"Error fetching messages from database: {str(e)}", exc_info=True)
                return None
                
        # Filter messages by date
        filtered_messages = filter_messages_by_date(messages, days)
        
        if not filtered_messages or len(filtered_messages) == 0:
            logger.warning(f"No messages found in the last {days} days")
            return None
            
        logger.info(f"Processing {len(filtered_messages)} messages")
        
        # Process messages for summarization
        processed_messages = message_processor.process_messages(filtered_messages)
        
        if not processed_messages or len(processed_messages) == 0:
            logger.warning("No messages could be processed")
            return None
            
        logger.info(f"Successfully processed {len(processed_messages)} messages")
        
        # Generate summary
        logger.info("Generating summary with OpenAI...")
        summary = openai_client.generate_summary(
            messages=processed_messages,
            days=days
        )
        
        if not summary or not isinstance(summary, str) or len(summary.strip()) == 0:
            logger.error("Failed to generate summary or empty summary returned")
            return None
            
        logger.info(f"Summary generated successfully ({len(summary)} chars)")
        
        # Store summary in database
        try:
            summary_data = {
                'group_id': group_id,
                'content': summary,
                'date': datetime.now().isoformat(),
                'message_count': len(processed_messages),
                'participants': list(set([msg.get('sender', 'unknown') for msg in filtered_messages])),
                'generated_at': datetime.now().isoformat(),
                'status': 'success'
            }
            
            # Try to store summary in database
            try:
                result = supabase.client.table('summaries').insert(summary_data).execute()
                logger.info("Summary stored in database")
            except Exception as e1:
                logger.warning(f"First storage method failed: {str(e1)}")
                try:
                    result = supabase.table('summaries').insert(summary_data).execute()
                    logger.info("Summary stored in database (alt method)")
                except Exception as e2:
                    logger.warning(f"Second storage method failed: {str(e2)}")
                    logger.error("Failed to store summary in database")
                
        except Exception as e:
            logger.error(f"Error storing summary: {str(e)}")
            # Continue anyway - storing the summary is not critical
            
        return summary
        
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}", exc_info=True)
        return None

def send_summary(components, group_id, summary):
    """
    Send a summary to a WhatsApp group
    
    Args:
        components (dict): Dictionary of initialized components
        group_id (str): ID of the WhatsApp group
        summary (str): Summary text to send
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    if not components or not group_id or not summary:
        logger.error("Invalid parameters for send_summary")
        return False
        
    try:
        # Check if message sending is disabled for safety
        config_manager = components.get('config_manager')
        if config_manager and config_manager.get('SEND_MESSAGES_DISABLED', 'True').lower() == 'true':
            logger.info("⛔ Message sending is currently disabled for safety.")
            print("\n⛔ Message sending is currently disabled for safety.")
            
            # Allow user to override if they confirm
            if confirm_action("Do you want to send the message anyway? This will override the safety setting."):
                logger.info("User chose to override safety setting and send message")
            else:
                logger.info("User chose not to override safety setting")
                print("\nSummary not sent to group.")
                return False
        
        # Get group manager
        group_manager = components.get('group_manager')
        if not group_manager:
            logger.error("Group manager not found in components")
            return False
            
        # Send message
        logger.info(f"Sending summary to group {group_id}")
        result = group_manager.send_message(group_id, summary)
        
        if result and isinstance(result, dict) and result.get('sent', False):
            logger.info("Summary sent successfully")
            return True
        else:
            logger.error(f"Failed to send summary: {result}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending summary: {str(e)}", exc_info=True)
        return False 