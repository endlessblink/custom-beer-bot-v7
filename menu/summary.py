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
import uuid
import os

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
    Filter messages based on the specified number of days.
    
    Args:
        messages (list): List of messages
        days (int): Number of days to filter
        
    Returns:
        list: Filtered messages
    """
    if not messages:
        logger.info("No messages to filter")
        return []
        
    if days is None or days <= 0:
        logger.info(f"No day filter applied (days={days}), returning all messages")
        return messages
        
    cutoff_date = datetime.now() - timedelta(days=days)
    logger.info(f"Filtering messages since {cutoff_date}")
    
    filtered_messages = []
    now = datetime.now()
    
    # Print debug info about first few messages for timestamp analysis
    if len(messages) > 0:
        logger.info(f"Analyzing timestamps of first message: {messages[0].get('timestamp')}, type: {type(messages[0].get('timestamp'))}")
        try:
            sample_msg = messages[0]
            logger.info(f"Sample message keys: {list(sample_msg.keys())}")
            if 'timestamp' in sample_msg:
                timestamp_value = sample_msg['timestamp']
                logger.info(f"Timestamp value: {timestamp_value}, Type: {type(timestamp_value)}")
                
                # Try to parse and display different interpretations of the timestamp
                if isinstance(timestamp_value, int):
                    try:
                        as_datetime = datetime.fromtimestamp(timestamp_value)
                        logger.info(f"As datetime (if seconds): {as_datetime}")
                        
                        as_datetime_ms = datetime.fromtimestamp(timestamp_value / 1000)
                        logger.info(f"As datetime (if milliseconds): {as_datetime_ms}")
                    except Exception as e:
                        logger.warning(f"Failed to interpret timestamp as datetime: {e}")
        except Exception as e:
            logger.warning(f"Error analyzing sample message: {e}")
    
    skipped_formats = set()
    processed_count = 0
    filtered_count = 0
    
    for message in messages:
        processed_count += 1
        try:
            if 'timestamp' not in message:
                logger.debug(f"Message has no timestamp field, skipping")
                continue
                
            timestamp = message['timestamp']
            msg_date = None
            
            # Handle different timestamp formats
            if isinstance(timestamp, str):
                try:
                    # Try parsing with timezone info
                    msg_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    # Convert to naive datetime for comparison
                    msg_date = msg_date.replace(tzinfo=None)
                except ValueError:
                    try:
                        # Try parsing without timezone info
                        msg_date = datetime.fromisoformat(timestamp)
                    except ValueError:
                        try:
                            # Try parsing with standard format
                            msg_date = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            logger.warning(f"Could not parse string timestamp: {timestamp}")
            
            # Handle integer timestamps (Unix timestamps)
            elif isinstance(timestamp, int) or isinstance(timestamp, float):
                try:
                    # Try as seconds since epoch (standard Unix timestamp)
                    msg_date = datetime.fromtimestamp(timestamp)
                except (ValueError, OSError, OverflowError):
                    try:
                        # Try as milliseconds since epoch
                        msg_date = datetime.fromtimestamp(timestamp / 1000)
                    except Exception as e2:
                        logger.warning(f"Could not parse integer timestamp {timestamp}: {e2}")
            
            elif isinstance(timestamp, datetime):
                # If it's already a datetime object, make sure it's naive for comparison
                msg_date = timestamp.replace(tzinfo=None) if timestamp.tzinfo else timestamp
            else:
                # Skip if timestamp is in an unsupported format
                format_type = type(timestamp).__name__
                if format_type not in skipped_formats:
                    skipped_formats.add(format_type)
                    logger.warning(f"Unsupported timestamp format: {format_type} - value: {timestamp}")
                continue
            
            if msg_date is None:
                logger.debug(f"Could not parse timestamp: {timestamp}")
                continue
                
            if msg_date >= cutoff_date:
                filtered_messages.append(message)
                filtered_count += 1
                
        except Exception as e:
            logger.warning(f"Error parsing message timestamp: {str(e)}")
    
    logger.info(f"Processed {processed_count} messages, filtered {filtered_count} messages after date filter")
    
    # Additional debug info on filtered messages
    if filtered_messages:
        try:
            # Get timestamp range of filtered messages
            timestamps = []
            for msg in filtered_messages:
                ts = msg.get('timestamp')
                if isinstance(ts, int) or isinstance(ts, float):
                    try:
                        timestamps.append(datetime.fromtimestamp(ts))
                    except:
                        try:
                            timestamps.append(datetime.fromtimestamp(ts / 1000))
                        except:
                            pass
                elif isinstance(ts, str):
                    try:
                        timestamps.append(datetime.fromisoformat(ts.replace('Z', '+00:00')))
                    except:
                        pass
                elif isinstance(ts, datetime):
                    timestamps.append(ts)
            
            if timestamps:
                oldest = min(timestamps)
                newest = max(timestamps)
                logger.info(f"Filtered message date range: {oldest} to {newest}")
        except Exception as e:
            logger.warning(f"Error analyzing filtered message dates: {e}")
    
    logger.info(f"Filtered {len(filtered_messages)} messages out of {len(messages)}")
    return filtered_messages

def generate_summary(components, group_id=None, days=None, use_api=True):
    """
    Generate a summary for a group's messages.
    
    Args:
        components (dict): Dictionary of initialized components
        group_id (str, optional): Group ID. If None, user will be prompted to select.
        days (int, optional): Number of days to include. If None, user will be prompted.
        use_api (bool): Whether to fetch new messages from API or use existing from DB
        
    Returns:
        str: Generated summary or None if errors occurred
    """
    try:
        # Log the start of summary generation
        logger.info(f"Starting summary generation process")
        
        # Validate components
        required_components = ['supabase_client', 'message_processor', 'openai_client']
        if use_api:
            required_components.append('group_manager')
            required_components.append('green_api_client')
            
        for component in required_components:
            if component not in components:
                error_msg = f"Missing required component: {component}"
                logger.error(error_msg)
                return None
                
        supabase_client = components['supabase_client']
        message_processor = components['message_processor']
        openai_client = components['openai_client']
        
        # Get group ID if not provided
        if not group_id:
            from menu.groups import select_group
            group = select_group(components)
            if not group or not isinstance(group, dict) or 'id' not in group:
                logger.error("No group selected for summary generation")
                return None
            group_id = group['id']
            logger.info(f"Selected group: {group.get('name', group_id)}")
                
        # Get number of days if not provided
        if days is None:
            days = select_days()
            if days is None:
                logger.error("No time period selected for summary generation")
                return None
                
        # Fetch messages based on the source selection (API or Database)
        messages = []
        
        if use_api:
            # Always try to get fresh messages from the API first
            logger.info(f"Generating summary for the last {days} days using fresh WhatsApp messages...")
            
            group_manager = components['group_manager']
            green_api = components['green_api_client']
            
            try:
                logger.info(f"Fetching latest messages from API for group {group_id}")
                
                # Always try to get at least 100 latest messages regardless of days
                print("\n📥 Fetching the latest messages from WhatsApp...")
                
                # Check which method is available and fetch at least 100 messages
                if hasattr(green_api, 'get_chat_history') and callable(getattr(green_api, 'get_chat_history')):
                    # Fetch 100 messages with minimum count set to 100
                    api_messages = green_api.get_chat_history(group_id, count=200, min_count=100)
                    logger.info(f"Used green_api.get_chat_history to fetch messages")
                elif hasattr(group_manager, 'get_chat_history') and callable(getattr(group_manager, 'get_chat_history')):
                    api_messages = group_manager.get_chat_history(group_id, count=200)
                    logger.info(f"Used group_manager.get_chat_history to fetch messages")
                else:
                    logger.error("No suitable method found to fetch chat history from API")
                    api_messages = []
                
                if api_messages and len(api_messages) > 0:
                    messages = api_messages
                    logger.info(f"Retrieved {len(messages)} messages from API")
                    print(f"✅ Retrieved {len(messages)} messages from WhatsApp")
                    
                    # Store messages in database for future use
                    try:
                        stored_count = supabase_client.store_messages(api_messages, group_id)
                        logger.info(f"Stored {stored_count} messages in database")
                        print(f"💾 Stored {stored_count} messages in database")
                    except Exception as e:
                        logger.warning(f"Could not store messages in database: {str(e)}")
                        # Continue with summary generation even if storage fails
                else:
                    logger.warning("No messages retrieved from API, falling back to database")
                    print("\n⚠️ Could not retrieve messages from WhatsApp, trying database...")
            except Exception as e:
                logger.error(f"Error fetching messages from API: {str(e)}", exc_info=True)
                print(f"\n❌ Error fetching messages from WhatsApp: {str(e)}")
                print("Falling back to database...")
                
        # If we don't have messages from API or not using API, try database
        if not messages:
            try:
                logger.info(f"Fetching messages from database for group {group_id}")
                print("\n📂 Searching for messages in database...")
                
                # Query database for messages from the group
                try:
                    result = supabase_client.client.table('messages').select('*').eq('group_id', group_id).order('timestamp', desc=True).limit(1000).execute()
                    db_messages = result.data
                except Exception as e1:
                    logger.warning(f"First query method failed: {str(e1)}")
                    try:
                        result = supabase_client.table('messages').select('*').eq('group_id', group_id).order('timestamp', desc=True).limit(1000).execute()
                        db_messages = result.data
                    except Exception as e2:
                        logger.warning(f"Second query method failed: {str(e2)}")
                        result = supabase_client.client.from_('messages').select('*').eq('group_id', group_id).order('timestamp', desc=True).limit(1000).execute()
                        db_messages = result.data
                
                logger.info(f"Found {len(db_messages)} messages in database")
                print(f"✅ Found {len(db_messages)} messages in database")
                
                # Convert to list of dicts if not already
                if db_messages and isinstance(db_messages, list):
                    if isinstance(db_messages[0], dict):
                        messages = db_messages
                    else:
                        # Try to convert to dict if it's some other object
                        try:
                            messages = [msg.__dict__ if hasattr(msg, '__dict__') else dict(msg) for msg in db_messages]
                        except:
                            messages = db_messages
                
            except Exception as e:
                logger.error(f"Error fetching messages from database: {str(e)}", exc_info=True)
                print(f"\n❌ Error fetching messages from database: {str(e)}")
                
        # Filter messages by date if days parameter is provided
        if messages and days:
            filtered_messages = filter_messages_by_date(messages, days)
            logger.info(f"Filtered from {len(messages)} to {len(filtered_messages)} messages based on {days} days filter")
            print(f"\n🔍 Filtered to {len(filtered_messages)} messages from the last {days} days")
            messages = filtered_messages
        
        # Check if we have messages to process
        if not messages or len(messages) == 0:
            logger.warning(f"No messages found in the selected period")
            print("\n❌ No messages found in the selected period")
            return None
            
        # Process messages and generate summary
        logger.info(f"Processing {len(messages)} messages for summary")
        print(f"\n⚙️ Processing {len(messages)} messages...")
        processed_content = message_processor.process_messages(messages)
        
        if not processed_content:
            logger.error("Failed to process messages for summary")
            print("\n❌ Failed to process messages")
            return None
            
        print(f"✅ Successfully processed {len(processed_content)} messages")
            
        # Generate summary
        logger.info("Generating summary from processed content")
        print("\n🤖 Generating summary...")
        summary = openai_client.generate_summary(processed_content)
        
        if not summary or summary.strip() == "":
            logger.error("Invalid summary generated")
            print("\n❌ Failed to generate summary")
            return None
            
        # Log the successful summary generation with the first part of its content
        summary_preview = summary[:50] + "..." if len(summary) > 50 else summary
        logger.info(f"Summary generated successfully ({len(summary)} chars): {summary_preview}")
        print(f"\n✅ Summary generated successfully ({len(summary)} characters)")
        
        # Save summary to file as a backup
        try:
            # Ensure directory exists
            os.makedirs('summaries', exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"summaries/summary_{timestamp}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(summary)
            print(f"\n✅ Summary saved to file: {filename}")
        except Exception as e:
            logger.warning(f"Could not save summary to file: {str(e)}")

        # Print the full summary for debugging/visibility with a much more visible frame
        if len(summary) > 0:
            print("\n")
            print("*" * 70)
            print("*" + " " * 24 + "GENERATED SUMMARY" + " " * 24 + "*")
            print("*" * 70)
            print()
            # Split by lines to make each line more visible
            for line in summary.split('\n'):
                print("  " + line)
            print()
            print("*" * 70)
            print("\n")
            
            # Also print char count for visibility
            print(f"Summary length: {len(summary)} characters")
            
            # Print first few characters in raw format for debugging
            print(f"First 10 characters (raw): {repr(summary[:10])}")
        
        # Store summary in database
        try:
            logger.info("Storing summary in database")
            
            # Create summary data with basic fields that should exist in all schemas
            summary_data = {
                'id': str(uuid.uuid4()),
                'group_id': group_id,
                'content': summary,
                'generated_at': datetime.now().isoformat(),
                'message_count': len(messages)
            }
            
            # Add optional fields - will be ignored if column doesn't exist
            try:
                summary_data['days_covered'] = days
                summary_data['status'] = 'generated'
            except:
                pass
            
            # Try different methods to insert the summary with error handling
            success = False
            errors = []
            
            # Method 1: Using client.from_
            try:
                logger.info("Attempting to store summary using client.from_ method")
                result = supabase_client.client.from_('summaries').insert(summary_data).execute()
                logger.info("Summary stored successfully using client.from_ method")
                success = True
            except Exception as e:
                error_msg = str(e)
                errors.append(f"Method 1 failed: {error_msg}")
                logger.warning(f"First insert method failed: {error_msg}")
                
                # If column doesn't exist error, try without that column
                if "Could not find the 'days_covered' column" in error_msg:
                    try:
                        logger.info("Retrying without days_covered field")
                        if 'days_covered' in summary_data:
                            del summary_data['days_covered']
                        result = supabase_client.client.from_('summaries').insert(summary_data).execute()
                        logger.info("Summary stored successfully after removing days_covered field")
                        success = True
                    except Exception as e2:
                        errors.append(f"Method 1 retry failed: {str(e2)}")
                        logger.warning(f"Retry without days_covered failed: {str(e2)}")
            
            # Method 2: Using client.table (if method 1 failed)
            if not success:
                try:
                    logger.info("Attempting to store summary using client.table method")
                    result = supabase_client.client.table('summaries').insert(summary_data).execute()
                    logger.info("Summary stored successfully using client.table method")
                    success = True
                except Exception as e:
                    errors.append(f"Method 2 failed: {str(e)}")
                    logger.warning(f"Second insert method failed: {str(e)}")
            
            # Method 3: Using direct attribute (if available)
            if not success and hasattr(supabase_client, 'store_summary'):
                try:
                    logger.info("Attempting to store summary using client.store_summary method")
                    result = supabase_client.store_summary(
                        summary=summary,
                        group_id=group_id,
                        message_count=len(messages)
                    )
                    logger.info("Summary stored successfully using store_summary method")
                    success = True
                except Exception as e:
                    errors.append(f"Method 3 failed: {str(e)}")
                    logger.warning(f"Third insert method failed: {str(e)}")
            
            if success:
                logger.info("Summary stored successfully")
            else:
                # Just log the error but continue - storage is not critical
                error_details = "; ".join(errors)
                logger.warning(f"Could not store summary in database after multiple attempts: {error_details}")
                
        except Exception as e:
            logger.error(f"Error storing summary: {str(e)}", exc_info=True)
            # Continue even if storage fails
            
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
        True: If sent successfully
        None: If user explicitly declined to send
        False: If failed due to technical error
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
                # Return None specifically to indicate user declined
                return None
        
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