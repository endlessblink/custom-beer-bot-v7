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
    
    # Initialize config manager
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
    try:
        supabase_client = SupabaseClient(
            url=config_manager.get('SUPABASE_URL'),
            key=config_manager.get('SUPABASE_KEY')
        )
    except Exception as e:
        logger.warning(f"Could not initialize Supabase client: {str(e)}")
        supabase_client = None
    
    return {
        'config_manager': config_manager,
        'green_api_client': green_api_client,
        'group_manager': group_manager,
        'openai_client': openai_client,
        'message_processor': message_processor,
        'supabase_client': supabase_client
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

def generate_summary(components, group_id, days=1, debug=False):
    """Generate a summary of recent messages"""
    green_api_client = components['green_api_client']
    message_processor = components['message_processor']
    openai_client = components['openai_client']
    supabase_client = components['supabase_client']
    
    print(f"\n⏳ Fetching messages for group {group_id}...")
    
    try:
        # Fetch recent messages
        messages = green_api_client.get_chat_history(group_id)
        
        if not messages:
            print("❌ No messages found to summarize.")
            return "אין הודעות לסיכום."
        
        print(f"✅ Found {len(messages)} messages")
        
        # Debug: Print example message structure
        if debug and messages:
            print("\n==== DEBUG: SAMPLE MESSAGE STRUCTURE ====")
            example_message = messages[0]
            print(f"Message keys: {list(example_message.keys())}")
            
            if 'messageData' in example_message:
                print(f"messageData keys: {list(example_message['messageData'].keys())}")
                
                # Check for the specific structure of the message
                message_data = example_message['messageData']
                for key in message_data:
                    if isinstance(message_data[key], dict):
                        print(f"  - {key} keys: {list(message_data[key].keys())}")
            
            print("Sample message info:")
            print(f"  - Sender: {example_message.get('senderName', 'Unknown')}")
            print(f"  - Type: {example_message.get('type', 'Unknown')}")
            print(f"  - Timestamp: {example_message.get('timestamp', 'Unknown')}")
            
            # Save raw messages to file for analysis
            try:
                import json
                import os
                # Create debug_logs directory if it doesn't exist
                os.makedirs('debug_logs', exist_ok=True)
                debug_filename = f"debug_logs/debug_messages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(debug_filename, 'w', encoding='utf-8') as f:
                    json.dump(messages[:5], f, indent=2, ensure_ascii=False)
                print(f"✅ Sample messages saved to {debug_filename}")
            except Exception as e:
                print(f"❌ Error saving debug file: {str(e)}")
                
            print("==== END DEBUG INFO ====\n")
        
        # Process messages
        print("⏳ Processing messages...")
        
        # Set debug mode in message processor
        if debug:
            message_processor.set_debug_mode(True)
            
        processed_messages = message_processor.process_messages(messages)
        
        if not processed_messages:
            print("❌ No valid messages to summarize after processing")
            
            if debug:
                print("\n==== DEBUG: MESSAGE PROCESSING ====")
                # Sample a few messages to understand why they were rejected
                print(f"Analyzing why messages were rejected:")
                sample_size = min(5, len(messages))
                for i, msg in enumerate(messages[:sample_size]):
                    print(f"\nSample message {i+1}:")
                    # Try to process and see what happens
                    result = message_processor._process_message(msg)
                    if result:
                        print(f"  ✓ Message would be ACCEPTED")
                    else:
                        msg_type = message_processor._get_message_type(msg)
                        text = message_processor._extract_text(msg, msg_type) if msg_type else "N/A"
                        print(f"  ✗ Message would be REJECTED")
                        print(f"    - Type detected: {msg_type}")
                        print(f"    - Text extracted: {text[:50]}...")
                        print(f"    - Sender: {msg.get('senderName', 'Unknown')}")
                
                print("\nTips for fixing:")
                print("1. Check message type detection in message_processor.py")
                print("2. Verify text extraction logic for these message types")
                print("3. Check if any message is being filtered out incorrectly")
                print("==== END DEBUG INFO ====\n")
                
            return "אין הודעות תקפות לסיכום."
        
        print(f"✅ Processed {len(processed_messages)} valid messages")
        
        # Debug: Show sample of processed messages
        if debug and processed_messages:
            print("\n==== DEBUG: SAMPLE PROCESSED MESSAGES ====")
            sample_size = min(3, len(processed_messages))
            for i, msg in enumerate(processed_messages[:sample_size]):
                print(f"Processed message {i+1}:")
                print(f"  - Sender: {msg.get('senderName', 'Unknown')}")
                print(f"  - Text: {msg.get('textMessage', '')[:100]}...")
                print(f"  - Type: {msg.get('type', 'Unknown')}")
                print(f"  - Time: {msg.get('timestamp', 'Unknown')}")
                print("")
            print("==== END DEBUG INFO ====\n")
        
        # Try to store messages in the database if available
        if supabase_client:
            try:
                print("⏳ Storing messages in database...")
                start_time = datetime.now()
                message_count = supabase_client.store_messages(processed_messages, group_id)
                print(f"✅ Stored {message_count} messages in database")
            except Exception as e:
                print(f"⚠️ Could not store messages in database: {str(e)}")
        
        # Generate summary
        print("⏳ Generating summary with OpenAI...")
        summary = openai_client.generate_summary(processed_messages)
        print("✅ Summary generated successfully")
        
        # Try to store the summary in the database if available
        if supabase_client:
            try:
                end_time = datetime.now()
                supabase_client.store_summary(
                    summary=summary,
                    group_id=group_id,
                    start_time=start_time,
                    end_time=end_time,
                    message_count=len(processed_messages),
                    model_used=openai_client.model
                )
                print("✅ Summary stored in database")
            except Exception as e:
                print(f"⚠️ Could not store summary in database: {str(e)}")
        
        return summary
        
    except Exception as e:
        print(f"❌ Error generating summary: {str(e)}")
        if debug:
            import traceback
            print("\n==== DEBUG: EXCEPTION TRACEBACK ====")
            traceback.print_exc()
            print("==== END TRACEBACK ====\n")
        return f"שגיאה בזמן יצירת הסיכום: {str(e)}"

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
    """Send the summary to the group"""
    config_manager = components['config_manager']
    green_api_client = components['green_api_client']
    
    # Check if dry run mode is enabled
    dry_run = config_manager.get('BOT_DRY_RUN', 'true').lower() == 'true'
    
    if dry_run:
        print("\n⚠️ DRY RUN mode is enabled in configuration.")
        choice = input("Would you like to override and send anyway? (y/n): ")
        if choice.lower() != 'y':
            print("❌ Summary was not sent due to DRY RUN mode.")
            return False
    
    print("\n⏳ Sending summary to the group...")
    response = green_api_client.send_message(group_id, summary, is_summary=True)
    
    if 'idMessage' in response and not response['idMessage'].startswith(('DISABLED', 'NON-SUMMARY')):
        print("✅ Summary sent to the group successfully!")
        return True
    else:
        print(f"❌ Failed to send summary: {response.get('message', 'Unknown error')}")
        return False

def view_previous_summaries(components):
    """View previous summaries stored in the database"""
    supabase_client = components['supabase_client']
    
    if not supabase_client:
        print("\n❌ Database connection not available.")
        return
    
    try:
        print("\n⏳ Fetching previous summaries...")
        summaries = supabase_client.get_summaries(limit=10)
        
        if not summaries:
            print("❌ No previous summaries found in the database.")
            return
        
        print("\nPrevious Summaries:")
        print("=" * 60)
        
        for i, summary in enumerate(summaries, 1):
            created_at = summary.get('created_at', 'Unknown date')
            try:
                # Convert the timestamp string to a datetime object
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    created_at = created_at.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
                
            group_id = summary.get('group_id', 'Unknown group')
            message_count = summary.get('message_count', 0)
            
            print(f"{i}. {created_at} - {message_count} messages")
        
        while True:
            selection = input("\nSelect a summary to view (number) or 'q' to go back: ")
            if selection.lower() == 'q':
                return
                
            try:
                selection = int(selection.strip())
                if selection < 1 or selection > len(summaries):
                    print("❌ Invalid selection. Please try again.")
                    continue
                
                # Display the selected summary
                selected = summaries[selection-1]
                print("\n" + "=" * 60)
                print(f"Summary from: {selected.get('created_at', 'Unknown date')}")
                print(f"Group ID: {selected.get('group_id', 'Unknown')}")
                print(f"Message count: {selected.get('message_count', 0)}")
                print(f"Model used: {selected.get('model_used', 'Unknown')}")
                print("=" * 60)
                print(selected.get('summary_text', 'Summary text not available'))
                print("=" * 60)
                
                input("\nPress Enter to continue...")
                break
                
            except ValueError:
                print("❌ Please enter a valid number.")
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                input("\nPress Enter to continue...")
                break
                
    except Exception as e:
        print(f"❌ Error fetching summaries: {str(e)}")

def show_main_menu():
    """Display the main menu and handle user interaction"""
    # Initialize components
    print("⏳ Initializing components...")
    components = initialize_components()
    print("✅ Components initialized successfully")
    
    while True:
        print_header()
        print("Main Menu:")
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
                print("Debug mode enabled - detailed information will be shown")
            
            # Generate summary
            print_header()
            print(f"Generating summary for {group['name']} ({days} day{'s' if days > 1 else ''})")
            summary = generate_summary(components, group['id'], days=days, debug=debug_mode)
            
            # Display the summary
            print("\n" + "=" * 60)
            print("SUMMARY:")
            print("=" * 60)
            print(summary)
            print("=" * 60)
            
            # Ask if user wants to send the summary
            send = input("\nDo you want to send this summary to the group? (y/n): ")
            if send.lower() == 'y':
                send_summary(components, group['id'], summary)
            
            input("\nPress Enter to continue...")
            
        elif choice == '2':
            # View Previous Summaries
            print_header()
            print("View Previous Summaries")
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
    try:
        show_main_menu()
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        logger.error(f"Unexpected error: {str(e)}") 