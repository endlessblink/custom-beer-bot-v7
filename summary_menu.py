#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Interactive Summary Menu

This script provides an interactive menu for generating and managing
WhatsApp group message summaries.

Usage:
    python summary_menu.py
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json
import time
import uuid
import openai

from config.config_manager import ConfigManager
from green_api.client import GreenAPIClient
from green_api.group_manager import GroupManager
from llm.openai_client import OpenAIClient
from processor.message_processor import MessageProcessor
from db.supabase_client import SupabaseClient
from utils.logger import setup_logger

# Setup logging
logger = setup_logger("INFO")

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print the application header"""
    clear_screen()
    print("=" * 60)
    print(" " * 15 + "WHATSAPP GROUP SUMMARY GENERATOR")
    print("=" * 60)
    print()

def initialize_components():
    """Initialize all necessary components"""
    # Load environment variables
    load_dotenv(override=True)
    
    # Load user settings (overrides env vars)
    load_user_settings()
    
    # Create config manager
    config_manager = ConfigManager()
    
    # Initialize Green API client
    green_api_client = GreenAPIClient(
        instance_id=config_manager.get('GREEN_API_ID_INSTANCE'),
        instance_token=config_manager.get('GREEN_API_TOKEN'),
        base_url=config_manager.get('GREEN_API_BASE_URL')
    )
    
    # Initialize Group Manager
    group_manager = GroupManager(green_api_client)
    
    # Initialize OpenAI client
    openai_client = OpenAIClient(
        api_key=config_manager.get('OPENAI_API_KEY'),
        model=config_manager.get('OPENAI_MODEL', 'gpt-4o-mini'),
        max_tokens=int(config_manager.get('OPENAI_MAX_TOKENS', 2000))
    )
    
    # Initialize message processor
    message_processor = MessageProcessor(
        target_language=config_manager.get('BOT_TARGET_LANGUAGE', 'hebrew')
    )
    
    # Initialize Supabase client (optional)
    supabase_client = None
    try:
        if config_manager.get('SUPABASE_URL') and config_manager.get('SUPABASE_KEY'):
            logger.info("Initializing Supabase client...")
            supabase_client = SupabaseClient(
                url=config_manager.get('SUPABASE_URL'),
                key=config_manager.get('SUPABASE_KEY')
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
        'supabase_client': supabase_client,
        'config_manager': config_manager
    }

def select_group(components):
    """Interactive group selection"""
    group_manager = components['group_manager']
    config_manager = components['config_manager']
    
    # Get groups from environment
    env_groups = []
    group_ids = config_manager.get('WHATSAPP_GROUP_IDS')
    if group_ids:
        env_groups = [gid.strip() for gid in group_ids.split(',') if gid.strip()]
    
    # Get preferred group from config
    preferred_group_id = config_manager.get('PREFERRED_GROUP_ID', '')
    
    # Get available groups from API
    try:
        api_groups = group_manager.get_groups()
    except Exception as e:
        logger.error(f"Error fetching groups: {str(e)}")
        print(f"❌ Failed to fetch groups: {str(e)}")
        api_groups = []
    
    # Combine and deduplicate groups
    all_groups = []
    seen_ids = set()
    preferred_group = None
    preferred_index = None
    
    # First add environment groups
    for group_id in env_groups:
        try:
            # Try to get group name
            group_data = group_manager.get_group_data(group_id)
            group_name = group_data.get('subject', 'Unknown Group')
            group_info = {
                'id': group_id,
                'name': group_name,
                'type': 'group'
            }
            
            all_groups.append(group_info)
            seen_ids.add(group_id)
            
            # Check if this is the preferred group
            if group_id == preferred_group_id:
                preferred_group = group_info
                preferred_index = len(all_groups) - 1
                
        except Exception:
            # If can't get group data, add with unknown name
            group_info = {
                'id': group_id,
                'name': 'Unknown Group',
                'type': 'group'
            }
            all_groups.append(group_info)
            seen_ids.add(group_id)
            
            # Check if this is the preferred group
            if group_id == preferred_group_id:
                preferred_group = group_info
                preferred_index = len(all_groups) - 1
    
    # Then add API groups that aren't already added
    for group in api_groups:
        if group['id'] not in seen_ids:
            all_groups.append(group)
            seen_ids.add(group['id'])
            
            # Check if this is the preferred group
            if group['id'] == preferred_group_id:
                preferred_group = group
                preferred_index = len(all_groups) - 1
    
    if not all_groups:
        print("❌ No groups available. Please join a WhatsApp group first.")
        return None
    
    print("\nAvailable WhatsApp Groups:")
    for i, group in enumerate(all_groups, 1):
        prefix = "→ " if group['id'] == preferred_group_id else "  "
        print(f"{prefix}{i}. {group['name']} ({group['id']})")
    
    # If we have a preferred group, offer it as default
    if preferred_group:
        print(f"\n→ Press Enter to select the preferred group: {preferred_group['name']}")
        
    while True:
        try:
            selection = input("\nSelect a group (number) or 'q' to quit: ")
            
            # Empty selection and we have a preferred group
            if selection.strip() == '' and preferred_group:
                print(f"\n✅ Selected preferred group: {preferred_group['name']}")
                return preferred_group
                
            if selection.lower() == 'q':
                return None
                
            selection = int(selection.strip())
            
            if selection < 1 or selection > len(all_groups):
                print("❌ Invalid selection. Please try again.")
                continue
            
            group_name = all_groups[selection-1]['name']
            group_id = all_groups[selection-1]['id']
            
            # If this is a new selection for the preferred group, offer to save it
            if preferred_group_id != group_id:
                save_as_preferred = input("Would you like to set this as your preferred group? (y/n): ")
                if save_as_preferred.lower() == 'y':
                    # We can't actually update the .env file automatically,
                    # but we can save it to a local settings file
                    try:
                        with open('user_settings.json', 'w') as f:
                            json.dump({'PREFERRED_GROUP_ID': group_id}, f)
                        print(f"✅ Saved as preferred group")
                    except Exception as e:
                        print(f"❌ Could not save preference: {str(e)}")
            
            print(f"\n✅ Selected group: {group_name}")
            return {
                'id': group_id,
                'name': group_name
            }
            
        except ValueError:
            print("❌ Please enter a valid number.")
        except Exception as e:
            print(f"❌ Error: {str(e)}")

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
            group_id = select_group(components)
            if not group_id:
                logger.error("No group selected for summary generation")
                return None
                
        # Get number of days if not provided
        if days is None:
            days = select_days()
            if days is None:
                logger.error("No time period selected for summary generation")
                return None
                
        # Fetch messages based on the source selection (API or Database)
        messages = []
        
        if use_api:
            # Try to get messages from the API
            logger.info(f"Generating summary for the last {days} days using fresh WhatsApp messages...")
            
            group_manager = components['group_manager']
            green_api = components['green_api_client']
            
            try:
                logger.info(f"Fetching messages from API for group {group_id}")
                
                # Minimum messages we want to work with after processing
                min_processed_messages = 100
                
                # Start with a higher count request to account for filtering
                initial_message_count = 200
                
                # Check which method is available for fetching chat history
                if hasattr(group_manager, 'get_chat_history') and callable(getattr(group_manager, 'get_chat_history')):
                    api_messages = group_manager.get_chat_history(group_id, count=initial_message_count, min_count=min_processed_messages)
                elif hasattr(green_api, 'get_chat_history') and callable(getattr(green_api, 'get_chat_history')):
                    api_messages = green_api.get_chat_history(group_id, count=initial_message_count, min_count=min_processed_messages)
                elif hasattr(group_manager, 'fetch_messages') and callable(getattr(group_manager, 'fetch_messages')):
                    api_messages = group_manager.fetch_messages(group_id, days)
                else:
                    logger.error("No suitable method found to fetch chat history from API")
                    api_messages = []
                
                if api_messages and len(api_messages) > 0:
                    messages = api_messages
                    logger.info(f"Retrieved {len(messages)} messages from API")
                else:
                    logger.warning("No messages retrieved from API, falling back to database")
            except Exception as e:
                logger.error(f"Error fetching messages from API: {str(e)}", exc_info=True)
                print(f"⚠️ API Error: {str(e)}")
                logger.info("Falling back to database for messages")
        
        # If we don't have messages yet or weren't using API, try to get from database
        if not messages:
            if not use_api:
                logger.info("Using database for messages instead of API")
                
            try:
                start_time = datetime.now() - timedelta(days=days)
                messages = supabase_client.get_messages(group_id, start_time)
                logger.info(f"Retrieved {len(messages)} messages from database")
            except Exception as e:
                logger.error(f"Error fetching messages from database: {str(e)}")
                print(f"⚠️ Database Error: {str(e)}")
                
        # If still no messages, abort
        if not messages:
            logger.error("No messages found from any source")
            print("❌ No messages found from any source. Cannot generate summary.")
            return "אין הודעות זמינות לסיכום."
        else:
            print(f"✅ Retrieved {len(messages)} messages")
        
        # Process the messages
        logger.info(f"Processing {len(messages)} messages")
        processed_messages = message_processor.process_messages(messages)
        
        # Check if we have enough processed messages
        min_messages_for_summary = 100
        attempts = 0
        max_attempts = 3
        
        while len(processed_messages) < min_messages_for_summary and attempts < max_attempts:
            attempts += 1
            logger.info(f"Only {len(processed_messages)} messages after processing, which is less than the minimum {min_messages_for_summary}. Fetching more (attempt {attempts}/{max_attempts})")
            print(f"\n⏳ Only {len(processed_messages)} messages after processing. Fetching more messages... (attempt {attempts}/{max_attempts})")
            
            try:
                # Double the count each time
                new_count = initial_message_count * (2 ** attempts)
                
                # Fetch more messages
                if hasattr(green_api, 'get_chat_history') and callable(getattr(green_api, 'get_chat_history')):
                    more_messages = green_api.get_chat_history(group_id, count=new_count, min_count=min_messages_for_summary*2)
                    if more_messages:
                        # Process the new messages
                        logger.info(f"Retrieved {len(more_messages)} additional messages")
                        more_processed = message_processor.process_messages(more_messages)
                        
                        # Combine with existing messages, avoiding duplicates
                        existing_ids = {msg.get('idMessage') for msg in processed_messages if 'idMessage' in msg}
                        for msg in more_processed:
                            if msg.get('idMessage') not in existing_ids:
                                processed_messages.append(msg)
                        
                        logger.info(f"Now have {len(processed_messages)} processed messages after fetching more")
                        print(f"✅ Now have {len(processed_messages)} processed messages")
                else:
                    logger.warning("Cannot fetch more messages - get_chat_history method not available")
                    break
            except Exception as e:
                logger.error(f"Error fetching additional messages: {str(e)}")
                print(f"⚠️ Error fetching more messages: {str(e)}")
                break
        
        # If still not enough messages, continue with what we have but log a warning
        if len(processed_messages) < min_messages_for_summary:
            logger.warning(f"Could only obtain {len(processed_messages)} processed messages, which is less than the ideal minimum {min_messages_for_summary}")
            print(f"\n⚠️ Could only obtain {len(processed_messages)} messages for summarization, which is less than the ideal minimum of {min_messages_for_summary}")
            
            if len(processed_messages) == 0:
                logger.error("No valid messages after processing")
                print("❌ No valid messages after processing. Cannot generate summary.")
                return "אין הודעות תקפות לסיכום אחרי עיבוד."
        else:
            print(f"\n✅ Successfully processed {len(processed_messages)} messages for summarization")
        
        # Try to store messages in the database
        if supabase_client:
            try:
                start_time = datetime.now() - timedelta(days=days)
                message_count = supabase_client.store_messages(processed_messages, group_id)
                logger.info(f"Stored {message_count} messages in database")
            except Exception as e:
                logger.warning(f"Could not store messages in database: {str(e)}")
                print(f"⚠️ Database storage warning: {str(e)}")
        
        # Generate the summary
        logger.info(f"Generating summary from {len(processed_messages)} messages")
        print(f"\n⏳ Generating summary from {len(processed_messages)} messages using OpenAI...")
        
        summary = openai_client.generate_summary(processed_messages)
        
        # Store the summary in the database
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
                print(f"⚠️ Database storage warning: {str(e)}")
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}", exc_info=True)
        if debug:
            print(f"\n❌ Error: {str(e)}")
            
            # Show detailed traceback in debug mode
            import traceback
            traceback.print_exc()
            
        return None

def select_days():
    """Select the number of days to summarize"""
    while True:
        try:
            days = input("\nEnter the number of days to summarize (default: 1): ")
            if not days:
                return 1
                
            days = int(days.strip())
            if days < 1:
                print("❌ Please enter a positive number.")
                continue
                
            return days
            
        except ValueError:
            print("❌ Please enter a valid number.")

def send_summary(components, group_id, summary):
    """Send a summary to a WhatsApp group"""
    green_api_client = components['green_api_client']
    config_manager = components['config_manager']
    
    # FORCE DISABLE MESSAGE SENDING - SAFETY MEASURE
    # This ensures messages are never sent accidentally
    message_sending_disabled = True
    
    # Previous settings checks (now just for information)
    config_disabled = config_manager.get('BOT_MESSAGE_SENDING_DISABLED', 'false').lower() == 'true'
    dry_run = config_manager.get('BOT_DRY_RUN', 'true').lower() == 'true'
    
    if message_sending_disabled:
        print("\n⛔ Message sending is currently disabled for safety.")
        print("To enable message sending in the future, contact the developer.")
        send_anyway = input("\nDo you want to try to send the message anyway? (y/n): ")
        if send_anyway.lower() != 'y':
            return None  # User declined to send
        # Continue trying if user insists
    
    # This code below will never execute due to the safety measure above
    # But we keep it for reference in case sending is re-enabled in the future
    if config_disabled:
        print("\n⛔ Message sending is disabled in configuration.")
        print("To enable, set BOT_MESSAGE_SENDING_DISABLED=false in .env")
        return None  # This is disabled by configuration
        
    if dry_run:
        print(f"\n⚠️ DRY RUN MODE - The summary would be sent to group {group_id}")
        print("To actually send messages, set BOT_DRY_RUN=false in .env")
        return None  # This is a dry run
    
    try:
        # Send the summary
        print("\n⏳ Sending summary to group...")
        response = green_api_client.send_message(group_id, summary, is_summary=True)
        
        if 'idMessage' in response and not response['idMessage'].startswith(('DISABLED', 'NON-SUMMARY')):
            print("✅ Summary sent successfully!")
            return True
        else:
            print(f"❌ Failed to send summary. Response: {response}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending summary: {str(e)}")
        return False

def view_previous_summaries(components):
    """View previously stored summaries"""
    supabase_client = components['supabase_client']
    
    if not supabase_client:
        print("\n❌ Database connection not available.")
        print("Previous summaries cannot be viewed without database access.")
        input("\nPress Enter to continue...")
        return
    
    try:
        print("\n⏳ Fetching previous summaries...")
        summaries = supabase_client.get_summaries(limit=10)
        
        if not summaries:
            print("\n⚠️ No summaries found in the database.")
            input("\nPress Enter to continue...")
            return
        
        while True:
            print_header()
            print("Previous Summaries:")
            print("-" * 60)
            
            for i, summary in enumerate(summaries, 1):
                # Format timestamp
                timestamp = summary.get('created_at', 'Unknown')
                if isinstance(timestamp, str):
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                
                # Get group ID and message count
                group_id = summary.get('group_id', 'Unknown')
                message_count = summary.get('message_count', 0)
                
                # Show summary information
                print(f"{i}. {timestamp} - Group: {group_id}")
                print(f"   Messages: {message_count}")
                print("-" * 60)
            
            print("\nOptions:")
            print("  [number] - View summary details")
            print("  b - Back to main menu")
            
            choice = input("\nEnter your choice: ")
            
            if choice.lower() == 'b':
                break
            
            try:
                index = int(choice) - 1
                if 0 <= index < len(summaries):
                    # Show the selected summary
                    selected = summaries[index]
                    
                    print_header()
                    print("Summary Details:")
                    print("=" * 60)
                    
                    # Format timestamps
                    created_at = selected.get('created_at', 'Unknown')
                    if isinstance(created_at, str):
                        try:
                            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            created_at = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            pass
                    
                    start_time = selected.get('start_time', 'Unknown')
                    if isinstance(start_time, str):
                        try:
                            dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                            start_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            pass
                    
                    end_time = selected.get('end_time', 'Unknown')
                    if isinstance(end_time, str):
                        try:
                            dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                            end_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            pass
                    
                    # Show summary metadata
                    print(f"Group ID: {selected.get('group_id', 'Unknown')}")
                    print(f"Created: {created_at}")
                    print(f"Period: {start_time} to {end_time}")
                    print(f"Message Count: {selected.get('message_count', 0)}")
                    print(f"Model: {selected.get('model_used', 'Unknown')}")
                    print("=" * 60)
                    
                    # Show the summary text
                    print("\nSUMMARY TEXT:")
                    print("-" * 60)
                    print(selected.get('summary_text', 'No text available'))
                    print("-" * 60)
                    
                    # Ask if user wants to resend this summary
                    resend = input("\nDo you want to resend this summary to a group? (y/n): ")
                    if resend.lower() == 'y':
                        # Select group
                        group = select_group(components)
                        if group:
                            send_summary(components, group['id'], selected.get('summary_text', ''))
                    
                else:
                    print("❌ Invalid selection")
                
            except ValueError:
                print("❌ Invalid input. Please enter a number or 'b'.")
                
            input("\nPress Enter to continue...")
                
    except Exception as e:
        print(f"❌ Error fetching summaries: {str(e)}")
        input("\nPress Enter to continue...")

def show_main_menu():
    """Display the main menu and handle user interaction"""
    # Initialize components
    print("⏳ Initializing components...")
    try:
        components = initialize_components()
        print("✅ Components initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing components: {str(e)}")
        print("⚠️ Some features may be limited")
        components = {}  # Empty components dict to allow basic menu functionality
    
    while True:
        print_header()
        print("Main Menu:")
        # Always show all menu options regardless of component status
        print("1. Generate New Summary")
        print("2. View Previous Summaries")
        print("3. Settings")
        print("4. Debug Mode")
        print("5. Exit")
        
        choice = input("\nEnter your choice: ")
        
        if choice == '1':
            # Generate New Summary
            print_header()
            print("Generate New Summary")
            
            # Check if necessary components are available
            if 'group_manager' not in components or 'openai_client' not in components:
                print("❌ Required components are not available.")
                print("Please check your configuration and try again.")
                input("\nPress Enter to continue...")
                continue
            
            # Select group
            group = select_group(components)
            if not group:
                print("⚠️ Group selection cancelled.")
                input("\nPress Enter to continue...")
                continue
            
            # Select days
            days = select_days()
            
            # Ask about debug mode
            debug_mode = False
            debug_choice = input("\nEnable debug mode? (y/n): ")
            if debug_choice.lower() == 'y':
                debug_mode = True
            
            # Generate the summary
            print("\n⏳ Generating summary... (this may take a minute)")
            try:
                summary = generate_summary(components, group['id'], days, debug_mode)
                
                if summary:
                    print("\n✅ Summary generated successfully!")
                    
                    # Display the summary with a more visible frame
                    print("\n" + "*" * 70)
                    print("*" + " " * 24 + "GENERATED SUMMARY" + " " * 24 + "*")
                    print("*" * 70)
                    print()
                    
                    # Split by lines for better visibility
                    for line in summary.split('\n'):
                        print("  " + line)
                    
                    print()
                    print("*" * 70)
                    print()
                    
                    # Ask if they want to send the summary to the group
                    send_choice = input("\nSend this summary to the group? (y/n): ")
                    if send_choice.lower() == 'y':
                        print("\n⏳ Sending summary to group...")
                        result = send_summary(components, group['id'], summary)
                        if result:
                            print("✅ Summary sent successfully!")
                        else:
                            print("❌ Failed to send summary to group.")
                else:
                    print("\n❌ Failed to generate summary.")
                    print("The summary generation process failed. This might be because:")
                    print("- No messages were found in the group")
                    print("- No messages matched the date range")
                    print("- All messages were filtered out during processing")
                    print("- There was an error during the OpenAI API call")
                    print("\nTry running again with debug mode enabled for more detailed information.")
            except ValueError as e:
                print(f"\n❌ Validation Error: {str(e)}")
                print("\nThis error occurred during input validation. Please check:")
                print("- The message data structure")
                print("- Whether there are any valid messages in the specified time period")
                print("- If the OpenAI API returned empty or invalid response")
                logger.error(f"Validation error in show_main_menu: {str(e)}", exc_info=True)
            except openai.APIError as e:
                print(f"\n❌ OpenAI API Error: {str(e)}")
                print("\nThis is a general error from the OpenAI API. Please check:")
                print("- Your internet connection")
                print("- OpenAI service status")
                print("- Your API key configuration")
                logger.error(f"OpenAI API error in show_main_menu: {str(e)}", exc_info=True)
            except openai.RateLimitError as e:
                print(f"\n❌ OpenAI Rate Limit Exceeded: {str(e)}")
                print("\nYou've hit the OpenAI API rate limit. Please:")
                print("- Wait a few minutes before trying again")
                print("- Consider upgrading your OpenAI plan if this happens frequently")
                logger.error(f"OpenAI rate limit error in show_main_menu: {str(e)}", exc_info=True)
            except openai.APIConnectionError as e:
                print(f"\n❌ OpenAI Connection Error: {str(e)}")
                print("\nCould not connect to the OpenAI API. Please check:")
                print("- Your internet connection")
                print("- Any network firewalls or proxy settings")
                logger.error(f"OpenAI connection error in show_main_menu: {str(e)}", exc_info=True)
            except openai.InvalidRequestError as e:
                print(f"\n❌ Invalid OpenAI Request: {str(e)}")
                print("\nThe request to OpenAI was invalid. This might be because:")
                print("- The message data contains invalid characters")
                print("- The prompt is too long (too many messages)")
                print("- There's an issue with your API key")
                logger.error(f"OpenAI invalid request error in show_main_menu: {str(e)}", exc_info=True)
            except Exception as e:
                print(f"\n❌ Error during summary generation: {str(e)}")
                print("The summary generation process encountered an error.")
                print("Try running again with debug mode enabled for more detailed information.")
                logger.error(f"Uncaught error in show_main_menu: {str(e)}", exc_info=True)
            
            input("\nPress Enter to continue...")
            
        elif choice == '2':
            # View Previous Summaries
            print_header()
            print("View Previous Summaries")
            
            # Check if database is available
            if 'supabase_client' not in components or not components['supabase_client']:
                print("❌ Database connection not available.")
                print("This feature requires a database connection.")
                input("\nPress Enter to continue...")
                continue
            
            view_previous_summaries(components)
            
        elif choice == '3':
            # Settings
            print_header()
            print("Settings")
            print("\nAvailable Settings:")
            
            config_manager = components['config_manager']
            settings = [
                ('BOT_DRY_RUN', 'Dry Run Mode', 'true/false'),
                ('BOT_TARGET_LANGUAGE', 'Target Language', 'hebrew/english/etc.'),
                ('OPENAI_MODEL', 'OpenAI Model', 'gpt-4o-mini/gpt-4/etc.'),
                ('BOT_MESSAGE_SENDING_DISABLED', 'Disable Message Sending', 'true/false')
            ]
            
            for i, (key, desc, options) in enumerate(settings, 1):
                value = config_manager.get(key, 'Not set')
                print(f"{i}. {desc}: {value} ({options})")
            
            # We won't implement actual setting changes in this version
            # as it would require writing to the .env file
            print("\n⚠️ To change settings, please edit the .env file directly.")
            input("\nPress Enter to continue...")
            
        elif choice == '4':
            # Debug Mode
            print_header()
            print("Debug Mode")
            print("\nDebug Options:")
            print("1. Analyze Message Structure")
            print("2. Test Specific Group")
            print("3. Check Connectivity")
            print("4. Back to Main Menu")
            
            debug_choice = input("\nEnter your choice: ")
            
            if debug_choice == '1':
                # Analyze Message Structure
                print("\nAnalyzing message structure...")
                
                # Select group
                group = select_group(components)
                if not group:
                    print("⚠️ Group selection cancelled.")
                    input("\nPress Enter to continue...")
                    continue
                
                # Get messages and analyze
                green_api_client = components['green_api_client']
                try:
                    messages = green_api_client.get_chat_history(group['id'])
                    if not messages:
                        print("❌ No messages found in this group.")
                    else:
                        print(f"✅ Found {len(messages)} messages")
                        
                        # Save raw messages to file for analysis
                        import json
                        import os
                        # Create debug_logs directory if it doesn't exist
                        os.makedirs('debug_logs', exist_ok=True)
                        debug_filename = f"debug_logs/debug_msgs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                        with open(debug_filename, 'w', encoding='utf-8') as f:
                            # Save just a sample to avoid too large files
                            json.dump(messages[:10], f, indent=2, ensure_ascii=False)
                        
                        print(f"✅ Sample messages saved to {debug_filename}")
                        print("\nExample message structure:")
                        example = messages[0]
                        print(f"Keys: {list(example.keys())}")
                        if 'messageData' in example:
                            print(f"messageData keys: {list(example['messageData'].keys())}")
                except Exception as e:
                    print(f"❌ Error: {str(e)}")
                    
                input("\nPress Enter to continue...")
                        
            elif debug_choice == '2':
                # Test Specific Group
                print("\nTesting specific group...")
                message_processor = components['message_processor']
                
                # Set debug mode
                message_processor.set_debug_mode(True)
                
                # Select group
                group = select_group(components)
                if not group:
                    print("⚠️ Group selection cancelled.")
                    input("\nPress Enter to continue...")
                    continue
                    
                # Generate summary with debug on
                generate_summary(components, group['id'], days=1, debug=True)
                input("\nPress Enter to continue...")
                
            elif debug_choice == '3':
                # Check Connectivity
                print("\nChecking connectivity...")
                
                # Test Green API connection
                green_api_client = components['green_api_client']
                try:
                    state = green_api_client.get_state()
                    print(f"✅ Green API connection: {state.get('stateInstance', 'Unknown')}")
                except Exception as e:
                    print(f"❌ Green API connection error: {str(e)}")
                
                # Test OpenAI connection
                openai_client = components['openai_client']
                try:
                    response = openai_client.test_connection()
                    print(f"✅ OpenAI connection: {response}")
                except Exception as e:
                    print(f"❌ OpenAI connection error: {str(e)}")
                    
                # Test Supabase connection
                supabase_client = components['supabase_client']
                if supabase_client:
                    try:
                        result = supabase_client.test_connection()
                        print(f"✅ Supabase connection: {result}")
                    except Exception as e:
                        print(f"❌ Supabase connection error: {str(e)}")
                else:
                    print("⚠️ Supabase client not initialized")
                    
                input("\nPress Enter to continue...")
                
            elif debug_choice == '4':
                continue
                
        elif choice == '5':
            # Exit
            print("\nExiting...")
            return
            
        else:
            print("\n❌ Invalid choice. Please try again.")
            time.sleep(1)

# Add a function to load user settings at startup
def load_user_settings():
    """Load user settings from file"""
    try:
        if os.path.exists('user_settings.json'):
            with open('user_settings.json', 'r') as f:
                settings = json.load(f)
                # Override environment variables with user settings
                for key, value in settings.items():
                    os.environ[key] = value
                logger.info(f"Loaded user settings: {settings}")
    except Exception as e:
        logger.error(f"Error loading user settings: {str(e)}")

if __name__ == "__main__":
    """
    WhatsApp Group Summary Generator Menu
    
    This is an interactive menu for generating and managing WhatsApp group summaries.
    
    Usage:
    1. Make sure you have set up your .env file with the necessary API keys
    2. Run the program: python summary_menu.py
    3. Use the menu to generate summaries, view previous ones, or change settings
    
    Note on database errors:
    If you encounter Supabase database errors, the program will continue to function
    with basic features, but without storing or retrieving previous summaries.
    """
    # Run the main menu
    try:
        show_main_menu()
    except KeyboardInterrupt:
        print("\n\nProgram terminated by user.")
    except Exception as e:
        print(f"\n\nAn unexpected error occurred: {str(e)}")
        
    print("\nGoodbye!") 