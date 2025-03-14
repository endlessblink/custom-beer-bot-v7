#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Interactive Summary Menu

This script provides an interactive menu for generating and managing
WhatsApp group message summaries.

Usage:
    python summary_menu_new.py
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json
import time

from config.config_manager import ConfigManager
from green_api.client import GreenAPIClient
from green_api.group_manager import GroupManager
from llm.openai_client import OpenAIClient
from processor.message_processor import MessageProcessor
from db.supabase_client import SupabaseClient
from utils.logger import setup_logger

# Import our core menu functionality - this ensures menu always works
from utils.menu.core_menu import (
    clear_screen, 
    print_header, 
    show_menu, 
    display_error_and_continue, 
    confirm_action
)

# Setup logging
logger = setup_logger("INFO")

def initialize_components():
    """Initialize all necessary components"""
    try:
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
        
        components = {
            'green_api_client': green_api_client,
            'group_manager': group_manager,
            'openai_client': openai_client,
            'message_processor': message_processor,
            'supabase_client': supabase_client,
            'config_manager': config_manager
        }
        
        logger.info("Components initialized successfully")
        return components
    
    except Exception as e:
        logger.error(f"Error initializing components: {str(e)}")
        # Return an empty components dictionary to allow the menu to still function
        logger.info("Returning empty components dictionary to ensure menu functionality")
        return {}

def select_group(components):
    """Select a WhatsApp group from the list of available groups"""
    try:
        group_manager = components.get('group_manager')
        if not group_manager:
            display_error_and_continue("Group manager not available")
            return None
        
        # Get the list of groups
        groups = group_manager.get_groups()
        
        if not groups:
            display_error_and_continue("No groups found or unable to fetch groups")
            return None
        
        # Display the groups
        group_options = [
            {'key': str(i+1), 'text': group['name'], 'group': group}
            for i, group in enumerate(groups)
        ]
        
        group_options.append({'key': 'c', 'text': 'Cancel'})
        
        choice = show_menu("Select a group", group_options)
        
        if choice == 'c':
            return None
        
        # Find the selected group
        for option in group_options:
            if option.get('key') == choice and 'group' in option:
                return option['group']
        
        return None
    
    except Exception as e:
        logger.error(f"Error selecting group: {str(e)}")
        display_error_and_continue(f"Error selecting group: {str(e)}")
        return None

def select_days():
    """Select the number of days of messages to summarize"""
    while True:
        print_header()
        print("Select Time Period:")
        print("1. Last 24 hours")
        print("2. Last 48 hours")
        print("3. Last 7 days")
        print("4. Custom")
        print("5. Back")
        
        choice = input("\nEnter your choice: ")
        
        if choice == '1':
            return 1
        elif choice == '2':
            return 2
        elif choice == '3':
            return 7
        elif choice == '4':
            try:
                days = int(input("\nEnter number of days: "))
                if days > 0:
                    return days
                else:
                    print("\n❌ Please enter a positive number")
                    time.sleep(1)
            except ValueError:
                print("\n❌ Please enter a valid number")
                time.sleep(1)
        elif choice == '5':
            return None
        else:
            print("\n❌ Invalid choice. Please try again.")
            time.sleep(1)

def generate_summary(components, group_id, days=1, debug=False):
    """Generate a summary of group messages"""
    try:
        green_api_client = components.get('green_api_client')
        openai_client = components.get('openai_client')
        message_processor = components.get('message_processor')
        supabase_client = components.get('supabase_client')
        
        if not green_api_client or not openai_client or not message_processor:
            display_error_and_continue("Missing required components for summary generation")
            return None
        
        # Get messages
        print("\n⏳ Fetching messages...")
        messages = green_api_client.get_chat_history(group_id)
        
        if debug:
            # Show message count
            print(f"\nFound {len(messages)} raw messages in the group")
            
            # Show a sample message
            if messages:
                print("\nSample message (first in list):")
                sample = messages[0]
                print(f"  Time: {datetime.fromtimestamp(sample.get('timestamp')).strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  From: {sample.get('senderName', 'Unknown')}")
                print(f"  Type: {sample.get('typeMessage', 'Unknown')}")
                if 'textMessage' in sample:
                    print(f"  Text: {sample.get('textMessage', '')[:50]}...")
            
            # Calculate and show date range
            if messages:
                try:
                    timestamps = [msg.get('timestamp') for msg in messages if 'timestamp' in msg]
                    if timestamps:
                        oldest = datetime.fromtimestamp(min(timestamps))
                        newest = datetime.fromtimestamp(max(timestamps))
                        print(f"\nMessage date range:")
                        print(f"  Oldest: {oldest.strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"  Newest: {newest.strftime('%Y-%m-%d %H:%M:%S')}")
                except Exception as e:
                    print(f"Error analyzing message dates: {str(e)}")
        
        # Process messages
        print("\n⏳ Processing messages...")
        processed_messages = message_processor.process_messages(messages)
        
        if debug:
            print(f"\nProcessed {len(processed_messages)} messages successfully")
        
        # Store messages in the database if available
        if supabase_client:
            try:
                stored_count = supabase_client.store_messages(processed_messages, group_id)
                print(f"\n✅ Stored {stored_count} messages in database")
            except Exception as e:
                logger.warning(f"Could not store messages in database: {str(e)}")
                if debug:
                    print(f"\n⚠️ Database error: {str(e)}")
        
        # Generate the summary
        print("\n⏳ Generating summary with OpenAI...")
        summary = openai_client.generate_summary(processed_messages)
        
        # Store the summary in the database if available
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
                print("\n✅ Stored summary in database")
            except Exception as e:
                logger.warning(f"Could not store summary in database: {str(e)}")
                if debug:
                    print(f"\n⚠️ Database error: {str(e)}")
        
        return summary
    
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        display_error_and_continue(f"Error generating summary: {str(e)}")
        return None

def send_summary(components, group_id, summary):
    """Send a summary to a WhatsApp group"""
    green_api_client = components.get('green_api_client')
    config_manager = components.get('config_manager')
    
    if not green_api_client or not config_manager:
        display_error_and_continue("Missing required components for sending summary")
        return False
    
    # FORCE DISABLE MESSAGE SENDING - SAFETY MEASURE
    # This ensures messages are never sent accidentally
    message_sending_disabled = True
    
    # Previous settings checks (now just for information)
    config_disabled = config_manager.get('BOT_MESSAGE_SENDING_DISABLED', 'false').lower() == 'true'
    dry_run = config_manager.get('BOT_DRY_RUN', 'true').lower() == 'true'
    
    if message_sending_disabled:
        print("\n⛔ Message sending is currently disabled for safety.")
        print("To enable message sending in the future, contact the developer.")
        return False
        
    # This code below will never execute due to the safety measure above
    # But we keep it for reference in case sending is re-enabled in the future
    if config_disabled:
        print("\n⛔ Message sending is disabled in configuration.")
        print("To enable, set BOT_MESSAGE_SENDING_DISABLED=false in .env")
        return False
        
    if dry_run:
        print(f"\n⚠️ DRY RUN MODE - The summary would be sent to group {group_id}")
        print("To actually send messages, set BOT_DRY_RUN=false in .env")
        return False
    
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
        logger.error(f"Error sending summary: {str(e)}")
        display_error_and_continue(f"Error sending summary: {str(e)}")
        return False

def view_previous_summaries(components):
    """View previously generated summaries"""
    try:
        supabase_client = components.get('supabase_client')
        
        if not supabase_client:
            display_error_and_continue("Database connection not available")
            return
        
        # Get summaries from the database
        summaries = supabase_client.get_summaries()
        
        if not summaries:
            display_error_and_continue("No previous summaries found")
            return
        
        # Display list of summaries
        summary_options = []
        for i, summary in enumerate(summaries):
            created_at = summary.get('created_at', 'Unknown date')
            if isinstance(created_at, str):
                date_str = created_at
            else:
                date_str = created_at.strftime('%Y-%m-%d %H:%M:%S') if created_at else 'Unknown date'
            
            group_id = summary.get('group_id', 'Unknown group')
            
            # Try to get group name
            group_name = "Unknown group"
            try:
                if 'group_manager' in components:
                    groups = components['group_manager'].get_groups()
                    for group in groups:
                        if group['id'] == group_id:
                            group_name = group['name']
                            break
            except:
                pass
            
            summary_options.append({
                'key': str(i+1),
                'text': f"{date_str} - {group_name}",
                'summary': summary
            })
        
        summary_options.append({'key': 'b', 'text': 'Back'})
        
        choice = show_menu("Select a summary to view", summary_options)
        
        if choice == 'b':
            return
        
        # Find the selected summary
        selected_summary = None
        for option in summary_options:
            if option.get('key') == choice and 'summary' in option:
                selected_summary = option['summary']
                break
        
        if not selected_summary:
            return
        
        # Display the selected summary
        print_header("Summary Details")
        
        created_at = selected_summary.get('created_at', 'Unknown date')
        if isinstance(created_at, str):
            date_str = created_at
        else:
            date_str = created_at.strftime('%Y-%m-%d %H:%M:%S') if created_at else 'Unknown date'
        
        print(f"Date: {date_str}")
        print(f"Group: {selected_summary.get('group_id', 'Unknown group')}")
        print(f"Messages: {selected_summary.get('message_count', 'Unknown')}")
        print(f"Model: {selected_summary.get('model_used', 'Unknown')}")
        print("\n" + "=" * 60)
        print("SUMMARY:")
        print("=" * 60)
        print(selected_summary.get('content', 'No content available'))
        print("=" * 60)
        
        input("\nPress Enter to continue...")
        
    except Exception as e:
        logger.error(f"Error viewing summaries: {str(e)}")
        display_error_and_continue(f"Error viewing summaries: {str(e)}")

def settings_menu(components):
    """Display the settings menu and handle user interaction"""
    config_manager = components.get('config_manager', {})
    
    while True:
        settings_options = [
            {'key': '1', 'text': 'Set Preferred Group'},
            {'key': '2', 'text': 'Set OpenAI Model', 'requires': ['openai_client']},
            {'key': '3', 'text': 'View Current Settings'},
            {'key': '4', 'text': 'Back'}
        ]
        
        choice = show_menu("Settings", settings_options, components)
        
        if choice == '1':
            # Set preferred group
            print_header("Set Preferred Group")
            
            if 'group_manager' not in components:
                display_error_and_continue("Group manager not available")
                continue
            
            group = select_group(components)
            if group:
                # Save preferred group ID to user settings
                save_user_setting('PREFERRED_GROUP_ID', group['id'])
                print(f"\n✅ Preferred group set to: {group['name']}")
                input("\nPress Enter to continue...")
            
        elif choice == '2':
            # Set OpenAI model
            print_header("Set OpenAI Model")
            
            if 'openai_client' not in components:
                display_error_and_continue("OpenAI client not available")
                continue
            
            models = [
                {'key': '1', 'text': 'GPT-4o', 'value': 'gpt-4o'},
                {'key': '2', 'text': 'GPT-4o-mini', 'value': 'gpt-4o-mini'},
                {'key': '3', 'text': 'GPT-3.5 Turbo', 'value': 'gpt-3.5-turbo'},
                {'key': '4', 'text': 'Claude 3 Opus', 'value': 'claude-3-opus-20240229'},
                {'key': '5', 'text': 'Claude 3 Sonnet', 'value': 'claude-3-sonnet-20240229'},
                {'key': '6', 'text': 'Claude 3 Haiku', 'value': 'claude-3-haiku-20240307'},
                {'key': '7', 'text': 'Cancel'}
            ]
            
            model_choice = show_menu("Select OpenAI Model", models)
            
            if model_choice == '7':
                continue
            
            # Find the selected model
            selected_model = None
            for model in models:
                if model.get('key') == model_choice and 'value' in model:
                    selected_model = model
                    break
            
            if selected_model:
                # Save model to user settings
                save_user_setting('OPENAI_MODEL', selected_model['value'])
                print(f"\n✅ OpenAI model set to: {selected_model['text']}")
                input("\nPress Enter to continue...")
            
        elif choice == '3':
            # View current settings
            print_header("Current Settings")
            
            # Load user settings
            user_settings = {}
            try:
                if os.path.exists('user_settings.json'):
                    with open('user_settings.json', 'r') as f:
                        user_settings = json.load(f)
            except Exception as e:
                print(f"❌ Error loading user settings: {str(e)}")
            
            # Display user settings
            print("User Settings:")
            if user_settings:
                for key, value in user_settings.items():
                    # For the preferred group, try to get the name
                    if key == 'PREFERRED_GROUP_ID' and 'group_manager' in components:
                        try:
                            groups = components['group_manager'].get_groups()
                            for group in groups:
                                if group['id'] == value:
                                    value = f"{value} ({group['name']})"
                                    break
                        except:
                            pass
                    
                    print(f"  {key}: {value}")
            else:
                print("  No user settings found")
            
            # Display environment variables
            print("\nEnvironment Variables:")
            env_vars = [
                'OPENAI_API_KEY', 
                'GREEN_API_ID_INSTANCE', 
                'GREEN_API_TOKEN',
                'SUPABASE_URL',
                'SUPABASE_KEY',
                'BOT_DRY_RUN',
                'BOT_MESSAGE_SENDING_DISABLED',
                'BOT_SUMMARY_INTERVAL',
                'BOT_TARGET_LANGUAGE'
            ]
            
            for var in env_vars:
                value = os.environ.get(var, 'Not set')
                # Mask sensitive values
                if 'KEY' in var or 'TOKEN' in var:
                    if value != 'Not set':
                        value = value[:4] + '****' + value[-4:] if len(value) > 8 else '****'
                
                print(f"  {var}: {value}")
            
            input("\nPress Enter to continue...")
            
        elif choice == '4':
            # Back to main menu
            return

def save_user_setting(key, value):
    """Save a user setting to the user_settings.json file"""
    try:
        # Load existing settings
        settings = {}
        if os.path.exists('user_settings.json'):
            with open('user_settings.json', 'r') as f:
                settings = json.load(f)
        
        # Update setting
        settings[key] = value
        
        # Save settings
        with open('user_settings.json', 'w') as f:
            json.dump(settings, f, indent=4)
        
        # Update environment variable
        os.environ[key] = value
        
        logger.info(f"Saved user setting: {key}={value}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving user setting: {str(e)}")
        return False

def debug_menu(components):
    """Display the debug menu and handle user interaction"""
    debug_options = [
        {'key': '1', 'text': 'Test API Connections'},
        {'key': '2', 'text': 'Export Message Data', 'requires': ['green_api_client']},
        {'key': '3', 'text': 'View Log Files'},
        {'key': '4', 'text': 'Back'}
    ]
    
    choice = show_menu("Debug Menu", debug_options, components)
    
    if choice == '1':
        # Test API connections
        print_header("Testing API Connections")
        
        # Test Green API connection
        if 'green_api_client' in components:
            green_api_client = components['green_api_client']
            try:
                state = green_api_client.get_state()
                print(f"✅ Green API connection: {state.get('stateInstance', 'Unknown')}")
            except Exception as e:
                print(f"❌ Green API connection error: {str(e)}")
        else:
            print("❌ Green API client not initialized")
        
        # Test OpenAI connection
        if 'openai_client' in components:
            openai_client = components['openai_client']
            try:
                response = openai_client.test_connection()
                print(f"✅ OpenAI connection: {response}")
            except Exception as e:
                print(f"❌ OpenAI connection error: {str(e)}")
        else:
            print("❌ OpenAI client not initialized")
            
        # Test Supabase connection
        if 'supabase_client' in components:
            supabase_client = components['supabase_client']
            try:
                result = supabase_client.test_connection()
                print(f"✅ Supabase connection: {result}")
            except Exception as e:
                print(f"❌ Supabase connection error: {str(e)}")
        else:
            print("⚠️ Supabase client not initialized")
            
        input("\nPress Enter to continue...")
        
    elif choice == '2':
        # Export message data
        print_header("Export Message Data")
        
        if 'green_api_client' not in components:
            display_error_and_continue("Green API client not available")
            return
        
        # Select group
        group = select_group(components)
        if not group:
            return
        
        # Get messages
        print("\n⏳ Fetching messages...")
        messages = components['green_api_client'].get_chat_history(group['id'])
        
        if not messages:
            display_error_and_continue("No messages found or unable to fetch messages")
            return
        
        # Create debug logs directory if it doesn't exist
        if not os.path.exists('debug_logs'):
            os.makedirs('debug_logs')
        
        # Save messages to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"debug_logs/debug_messages_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=4, ensure_ascii=False)
        
        print(f"\n✅ Exported {len(messages)} messages to {filename}")
        input("\nPress Enter to continue...")
        
    elif choice == '3':
        # View log files
        print_header("View Log Files")
        
        # Check if debug_logs directory exists
        if not os.path.exists('debug_logs'):
            display_error_and_continue("No log files found")
            return
        
        # Get log files
        log_files = [f for f in os.listdir('debug_logs') if f.endswith('.log')]
        
        if not log_files:
            display_error_and_continue("No log files found")
            return
        
        # Display log files
        log_options = [
            {'key': str(i+1), 'text': log_file}
            for i, log_file in enumerate(log_files)
        ]
        
        log_options.append({'key': 'b', 'text': 'Back'})
        
        log_choice = show_menu("Select a log file to view", log_options)
        
        if log_choice == 'b':
            return
        
        # Find the selected log file
        selected_log = None
        for option in log_options:
            if option.get('key') == log_choice and 'text' in option:
                selected_log = option['text']
                break
        
        if not selected_log:
            return
        
        # Display the log file
        print_header(f"Log File: {selected_log}")
        
        try:
            with open(f"debug_logs/{selected_log}", 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
                # Display last 50 lines
                print("Showing last 50 lines:")
                print("=" * 60)
                for line in lines[-50:]:
                    print(line.strip())
                print("=" * 60)
                
            input("\nPress Enter to continue...")
            
        except Exception as e:
            display_error_and_continue(f"Error reading log file: {str(e)}")
    
    elif choice == '4':
        # Back to main menu
        return

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

def run_main_menu():
    """Display the main menu and handle user interaction"""
    # Initialize components
    print("⏳ Initializing components...")
    components = initialize_components()
    
    # Define main menu options
    main_menu_options = [
        {'key': '1', 'text': 'Generate New Summary', 'requires': ['group_manager', 'openai_client']},
        {'key': '2', 'text': 'Settings'},
        {'key': '3', 'text': 'Debug Mode'},
        {'key': '4', 'text': 'Exit'}
    ]
    
    while True:
        choice = show_menu("Main Menu", main_menu_options, components)
        
        if choice == '1':
            # Generate New Summary
            group = select_group(components)
            if not group:
                continue
            
            days = select_days()
            if not days:
                continue
            
            debug_mode = confirm_action("Enable debug mode?")
            
            summary = generate_summary(components, group['id'], days, debug_mode)
            
            if summary:
                print("\n✅ Summary generated successfully!")
                print("\n" + summary)
                
                should_send = confirm_action("Send this summary to the group?")
                if should_send:
                    send_summary(components, group['id'], summary)
            
            input("\nPress Enter to continue...")
            
        elif choice == '2':
            # Settings
            settings_menu(components)
            
        elif choice == '3':
            # Debug Mode
            debug_menu(components)
            
        elif choice == '4':
            # Exit
            print("\nExiting...")
            return

if __name__ == "__main__":
    """
    WhatsApp Group Summary Generator Menu
    
    This is an interactive menu for generating and managing WhatsApp group summaries.
    
    Usage:
    1. Make sure you have set up your .env file with the necessary API keys
    2. Run the program: python summary_menu_new.py
    3. Use the menu to generate summaries, view previous ones, or change settings
    
    Note on database errors:
    If you encounter Supabase database errors, the program will continue to function
    with basic features, but without storing or retrieving previous summaries.
    """
    try:
        run_main_menu()
    except KeyboardInterrupt:
        print("\n\nProgram terminated by user.")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        print(f"\n\nAn unexpected error occurred: {str(e)}")
        
    print("\nGoodbye!") 