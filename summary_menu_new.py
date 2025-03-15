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
import random
import threading
import schedule
import signal

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

class BackgroundBot:
    """
    Background mode for the WhatsApp Summary Bot
    Allows the bot to run as a daemon and perform scheduled tasks
    """
    
    def __init__(self):
        self.components = None
        self.running = False
        self.scheduler_thread = None
        self.logger = logging.getLogger(__name__)
        self.scheduled_time = None
        self.test_group_id = None
        self.source_group_id = None  # Source group for fetching messages
        self.target_group_id = None  # Target group for posting summaries
    
    def initialize(self):
        """Initialize components for background operation"""
        print("⏳ Initializing bot components for background operation...")
        try:
            self.components = initialize_components()
            # Load user settings
            load_user_settings()
            
            # Get group configurations
            self.source_group_id = os.environ.get('SOURCE_GROUP_ID', os.environ.get('PREFERRED_GROUP_ID'))
            self.target_group_id = os.environ.get('TARGET_GROUP_ID')
            self.test_group_id = os.environ.get('TEST_GROUP_ID')
            
            # Get scheduled time if configured
            self.scheduled_time = os.environ.get('SCHEDULED_POST_TIME')
            return True
        except Exception as e:
            print(f"❌ Error initializing components: {str(e)}")
            self.logger.error(f"Error initializing components: {str(e)}")
            return False
    
    def setup_scheduler(self):
        """Setup scheduled tasks"""
        # Clear any existing jobs
        schedule.clear()
        
        # If scheduled time is set, create a daily job
        if self.scheduled_time:
            try:
                # Parse time in format HH:MM
                hour, minute = self.scheduled_time.split(':')
                hour, minute = int(hour), int(minute)
                
                # Schedule daily summary generation
                schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(self.generate_daily_summary)
                print(f"✅ Scheduled daily summary generation at {hour:02d}:{minute:02d}")
                self.logger.info(f"Scheduled daily summary generation at {hour:02d}:{minute:02d}")
            except Exception as e:
                print(f"❌ Error setting up scheduler: {str(e)}")
                self.logger.error(f"Error setting up scheduler: {str(e)}")
    
    def scheduler_loop(self):
        """Run the scheduler loop"""
        while self.running:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds
    
    def generate_daily_summary(self):
        """Generate and send daily summary"""
        try:
            self.logger.info("Starting scheduled daily summary generation")
            print("\n⏳ Generating scheduled daily summary...")
            
            # Get the source group ID (where to fetch messages from)
            source_group_id = self.source_group_id
            if not source_group_id:
                self.logger.error("No source group configured for fetching messages")
                print("❌ No source group configured for fetching messages")
                return
            
            # Determine where to send the summary
            # Priority: 1. Test group (if exists), 2. Target group (if exists), 3. Source group
            if self.test_group_id:
                target_group_id = self.test_group_id
                target_type = "test"
            elif self.target_group_id:
                target_group_id = self.target_group_id
                target_type = "target"
            else:
                target_group_id = source_group_id
                target_type = "source"
            
            # Get group names for better display
            source_group_name = "Unknown"
            target_group_name = "Unknown"
            
            try:
                group_manager = self.components.get('group_manager')
                if group_manager:
                    groups = group_manager.get_groups()
                    for group in groups:
                        if group['id'] == source_group_id:
                            source_group_name = group['name']
                        if group['id'] == target_group_id:
                            target_group_name = group['name']
            except Exception as e:
                self.logger.warning(f"Could not retrieve group names: {str(e)}")
            
            # First, fetch new messages from the source group
            print(f"⏳ Fetching new messages from source group: {source_group_name} ({source_group_id})...")
            auto_fetch_new_messages(self.components, group_id=source_group_id, background_mode=True)
            
            # Generate summary for the last 24 hours from the source group
            days = 1
            debug_mode = False
            summary = generate_summary(self.components, source_group_id, days, debug_mode, background_mode=True)
            
            if summary:
                print("\n✅ Summary generated successfully!")
                
                # Send to the appropriate target group
                print(f"⏳ Sending summary to {target_type} group: {target_group_name} ({target_group_id})...")
                send_summary(self.components, target_group_id, summary, background_mode=True)
                print("✅ Summary sent successfully!")
                
                self.logger.info(f"Scheduled summary sent: Source={source_group_name} ({source_group_id}), Target={target_group_name} ({target_group_id})")
            else:
                print("❌ Failed to generate summary")
                self.logger.error("Failed to generate scheduled summary")
        
        except Exception as e:
            print(f"❌ Error in scheduled summary generation: {str(e)}")
            self.logger.error(f"Error in scheduled summary generation: {str(e)}")
    
    def start(self):
        """Start the background bot"""
        if self.running:
            print("⚠️ Bot is already running")
            return
        
        if not self.components and not self.initialize():
            print("❌ Failed to initialize bot components")
            return
        
        print("🤖 Starting bot in background mode...")
        self.running = True
        
        # Setup scheduler
        self.setup_scheduler()
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self.scheduler_loop)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        # Get group names for better display
        source_group_name = "Unknown"
        target_group_name = "Unknown"
        test_group_name = "Unknown"
        
        try:
            group_manager = self.components.get('group_manager')
            if group_manager:
                groups = group_manager.get_groups()
                for group in groups:
                    if group['id'] == self.source_group_id:
                        source_group_name = group['name']
                    if self.target_group_id and group['id'] == self.target_group_id:
                        target_group_name = group['name']
                    if self.test_group_id and group['id'] == self.test_group_id:
                        test_group_name = group['name']
        except Exception as e:
            self.logger.warning(f"Could not retrieve group names: {str(e)}")
        
        print("✅ Bot is now running in the background")
        print(f"📅 {'Scheduled to post daily at ' + self.scheduled_time if self.scheduled_time else 'No scheduled posting configured'}")
        
        if self.test_group_id:
            print(f"📥 Source: {source_group_name} ({self.source_group_id})")
            print(f"📤 Target: {test_group_name} ({self.test_group_id}) [TEST MODE]")
        elif self.target_group_id:
            print(f"📥 Source: {source_group_name} ({self.source_group_id})")
            print(f"📤 Target: {target_group_name} ({self.target_group_id})")
        else:
            print(f"📥 Source & Target: {source_group_name} ({self.source_group_id})")
            
        print("\nPress Ctrl+C to stop the bot")
        
        # Keep the main thread alive until interrupted
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the background bot"""
        print("\n⏹️ Stopping background bot...")
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=2)
        print("✅ Bot stopped")

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
            {'key': str(i+1), 'text': f"{group['name']} ({group['id']})", 'group': group}
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

def generate_summary(components, group_id, days=1, debug=False, background_mode=False):
    """Generate a summary of group messages"""
    try:
        green_api_client = components.get('green_api_client')
        openai_client = components.get('openai_client')
        message_processor = components.get('message_processor')
        supabase_client = components.get('supabase_client')
        
        if not green_api_client or not openai_client or not message_processor:
            display_error_and_continue("Missing required components for summary generation")
            return None
        
        # Fetch and store the latest messages from the group first
        if supabase_client:
            print("\n📱 Fetching the latest messages to ensure fresh data...")
            fetch_messages = green_api_client.get_chat_history(group_id, count=800, min_count=500)
            if fetch_messages:
                print(f"✅ Retrieved {len(fetch_messages)} messages")
                stored_count = supabase_client.store_messages(fetch_messages, group_id)
                print(f"✅ Stored {stored_count} new messages in the database")
            else:
                print("⚠️ Could not fetch new messages, proceeding with existing data")
        
        # Set higher request limits to ensure we get enough data
        message_request_count = 800  # Increased from 500
        message_min_count = 500  # Increased from 300
        
        # Get fresh messages directly from WhatsApp - always force fresh data
        print("\n📱 Fetching fresh messages from WhatsApp...")
        print(f"⏳ Requesting {message_request_count} messages with minimum {message_min_count}...")
        messages = green_api_client.get_chat_history(group_id, count=message_request_count, min_count=message_min_count)
        
        if not messages:
            print("\n❌ No messages retrieved from WhatsApp")
            if debug:
                print("\nDiagnostic information:")
                print("- The Green API client was unable to fetch messages")
                print("- This could be due to connection issues with WhatsApp")
                print("- You might want to check your Green API credentials")
                
                # Offer retry options
                if confirm_action("Would you like to try again with different parameters?"):
                    retry_count = int(input("\nHow many messages to request (default: 200): ") or "200")
                    messages = green_api_client.get_chat_history(group_id, count=retry_count)
                    if not messages:
                        print("\n❌ Still no messages retrieved. Falling back to database.")
                    else:
                        print(f"\n✅ Retrieved {len(messages)} messages on retry.")
            
            # If still no messages, try database
            if not messages:
                print("\n📂 Checking database for existing messages...")
                try:
                    result = supabase_client.client.table('messages').select('*').eq('group_id', group_id).order('timestamp', desc=True).limit(1000).execute()
                    db_messages = result.data
                    if db_messages and len(db_messages) > 0:
                        print(f"\n✅ Found {len(db_messages)} messages in database")
                        messages = db_messages
                    else:
                        print("\n❌ No messages found in database either")
                        return None
                except Exception as e:
                    print(f"\n❌ Error accessing database: {str(e)}")
                    return None
        else:
            print(f"\n✅ Successfully retrieved {len(messages)} messages from WhatsApp")
            
            # Store retrieved messages in database for future use
            if supabase_client:
                try:
                    stored_count = supabase_client.store_messages(messages, group_id)
                    print(f"\n💾 Stored {stored_count} messages in database")
                except Exception as e:
                    print(f"\n⚠️ Could not store messages in database: {str(e)}")
                    # Continue with summary generation even if storage fails
        
        # Debug information
        if debug:
            # Show message count
            print(f"\nFound {len(messages)} raw messages in the group")
            
            # Show message types
            message_types = {}
            for msg in messages:
                msg_type = msg.get('typeMessage', 'unknown')
                message_types[msg_type] = message_types.get(msg_type, 0) + 1
            print(f"\nMessage types: {message_types}")
            
            # Show a sample message
            if messages:
                print("\nSample message (first in list):")
                sample = messages[0]
                print(f"  Keys: {list(sample.keys())}")
                
                if 'timestamp' in sample:
                    timestamp = sample.get('timestamp')
                    print(f"  Timestamp: {timestamp} (type: {type(timestamp).__name__})")
                    
                    # Try to convert timestamp if needed
                    try:
                        if isinstance(timestamp, str):
                            if timestamp.isdigit():
                                timestamp = int(timestamp)
                            # If it's already a date string, we'll leave it as is
                        
                        if isinstance(timestamp, int):
                            time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                            print(f"  Time: {time_str}")
                        else:
                            print(f"  Time (as string): {timestamp}")
                    except Exception as e:
                        print(f"  Error converting timestamp: {str(e)}")
                        
                print(f"  From: {sample.get('senderName', 'Unknown')}")
                print(f"  Type: {sample.get('typeMessage', 'Unknown')}")
                if 'textMessage' in sample:
                    print(f"  Text: {sample.get('textMessage', '')[:50]}...")
            
            # Calculate and show date range
            if messages:
                try:
                    # Handle both string and integer timestamps
                    timestamps = []
                    for msg in messages:
                        if 'timestamp' in msg and msg['timestamp'] is not None:
                            try:
                                if isinstance(msg['timestamp'], str):
                                    if msg['timestamp'].isdigit():
                                        timestamps.append(int(msg['timestamp']))
                                    else:
                                        # For date strings, just note that they exist
                                        print(f"  Found date string timestamp: {msg['timestamp']}")
                                else:
                                    timestamps.append(msg['timestamp'])
                            except (ValueError, TypeError):
                                pass
                    
                    if timestamps:
                        oldest = datetime.fromtimestamp(min(timestamps))
                        newest = datetime.fromtimestamp(max(timestamps))
                        print(f"\nMessage date range:")
                        print(f"  Oldest: {oldest.strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"  Newest: {newest.strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        # Check if the newest message is very recent (within the last hour)
                        now = datetime.now()
                        if (now - newest).total_seconds() < 3600:  # Less than 1 hour
                            print("  ✅ Recent messages found - data is up to date")
                        else:
                            print(f"  ⚠️ Most recent message is from {(now - newest).total_seconds() / 3600:.1f} hours ago")
                            if confirm_action("Try to fetch more recent messages?"):
                                print("\n⏳ Fetching more recent messages...")
                                more_recent = green_api_client.get_chat_history(group_id, count=100)
                                if more_recent and len(more_recent) > 0:
                                    # Check the timestamp of the first message (should be most recent)
                                    try:
                                        most_recent_ts = more_recent[0].get('timestamp')
                                        if most_recent_ts:
                                            if isinstance(most_recent_ts, str) and most_recent_ts.isdigit():
                                                most_recent_ts = int(most_recent_ts)
                                            most_recent_time = datetime.fromtimestamp(most_recent_ts)
                                            print(f"  Most recent message: {most_recent_time.strftime('%Y-%m-%d %H:%M:%S')}")
                                            
                                            # Add these more recent messages to our list
                                            messages = more_recent + messages
                                            print(f"  ✅ Added {len(more_recent)} more recent messages")
                                    except Exception as e:
                                        print(f"  Error processing recent messages: {str(e)}")
                                else:
                                    print("  No more recent messages found")
                except Exception as e:
                    print(f"Error analyzing message dates: {str(e)}")
        
        # Check if we have any messages at all
        if not messages:
            print("\n⚠️ No messages found in the group. Cannot generate summary.")
            if debug:
                print("DEBUG: API returned an empty list of messages. Possible causes:")
                print("1. The group is new or has no message history")
                print("2. The API credentials don't have access to this group")
                print("3. There's an issue with the API connection")
            
            if confirm_action("Would you like to try again with different parameters?"):
                print("\n⏳ Retrying with higher message count...")
                messages = green_api_client.get_chat_history(group_id, count=1500, min_count=1000)  # Even higher counts
                if not messages:
                    display_error_and_continue("Still no messages found. Unable to generate summary.")
                    return None
                print(f"✅ Retrieved {len(messages)} messages on second attempt!")
            else:
                return None
        
        # Process messages - enable debug mode to get more visibility
        print("\n⏳ Processing messages...")
        # If possible, always enable debug mode when a debugging session is active
        if hasattr(message_processor, 'set_debug_mode') and debug:
            message_processor.set_debug_mode(True)
            print("Debug mode enabled for message processor")
        
        # Try with reduced filtering first for better results
        if hasattr(message_processor, 'reduced_filtering'):
            message_processor.reduced_filtering = True
            print("Using reduced filtering to include more message content")
        
        processed_messages = message_processor.process_messages(messages)
        
        if debug:
            print(f"\nProcessed {len(processed_messages)} messages successfully")
            # Show processed message types
            processed_types = {}
            for msg in processed_messages:
                msg_type = msg.get('typeMessage', 'unknown')
                processed_types[msg_type] = processed_types.get(msg_type, 0) + 1
            print(f"\nProcessed message types: {processed_types}")
            
            # Verify if messages have timestamps
            timestamps_present = sum(1 for msg in processed_messages if 'timestamp' in msg and msg['timestamp'] is not None)
            print(f"Messages with timestamps: {timestamps_present} out of {len(processed_messages)}")
            
        # Check if we have enough processed messages after filtering
        min_messages_for_summary = 200  # Increased from 100
        
        # If we have too few processed messages, try again with more lenient processing
        if len(processed_messages) < min_messages_for_summary:
            print(f"\n⚠️ Only {len(processed_messages)} messages after processing, which is less than minimum {min_messages_for_summary}.")
            
            # Try to improve the situation
            if hasattr(message_processor, 'reduced_filtering') and not message_processor.reduced_filtering:
                print("Enabling reduced filtering to include more messages...")
                message_processor.reduced_filtering = True
                processed_messages = message_processor.process_messages(messages)
                print(f"After reduced filtering: {len(processed_messages)} messages")
            
            # If still not enough, fetch more
            if len(processed_messages) < min_messages_for_summary:
                print("Fetching more messages...")
                
                # Try to fetch more messages in batches
                attempts = 0
                max_attempts = 3
                
                while len(processed_messages) < min_messages_for_summary and attempts < max_attempts:
                    attempts += 1
                    print(f"⏳ Fetching more messages (attempt {attempts}/{max_attempts})...")
                    
                    # Increase batch size exponentially
                    new_count = message_request_count * (2 ** attempts)
                    new_min = min_messages_for_summary * (attempts + 1)
                    
                    try:
                        # Fetch more messages
                        print(f"⏳ Requesting {new_count} messages with minimum {new_min}...")
                        more_messages = green_api_client.get_chat_history(group_id, count=new_count, min_count=new_min)
                        if more_messages:
                            print(f"✅ Retrieved {len(more_messages)} additional messages")
                            
                            # Process the new messages
                            more_processed = message_processor.process_messages(more_messages)
                            print(f"✅ Processed {len(more_processed)} additional messages")
                            
                            # Combine with existing messages, avoiding duplicates
                            existing_ids = {msg.get('idMessage') for msg in processed_messages if 'idMessage' in msg}
                            new_count = 0
                            for msg in more_processed:
                                if msg.get('idMessage') not in existing_ids:
                                    processed_messages.append(msg)
                                    new_count += 1
                                    
                            print(f"✅ Added {new_count} new unique messages, now have {len(processed_messages)} processed messages")
                        else:
                            print("⚠️ No additional messages returned")
                            break
                    except Exception as e:
                        print(f"❌ Error fetching additional messages: {str(e)}")
                        break
        
        if len(processed_messages) < min_messages_for_summary:
            print(f"\n⚠️ Could only obtain {len(processed_messages)} messages for summarization, which is less than the ideal minimum of {min_messages_for_summary}")
            
            # If we have very few messages, they might be special messages that need careful handling
            if len(processed_messages) < 10:
                print("\n⚠️ Very few messages available. This might indicate a new group or access restrictions.")
                
                if debug:
                    print("\nRemaining messages after processing:")
                    for i, msg in enumerate(processed_messages[:5]):  # Show up to 5 messages
                        msg_type = msg.get('typeMessage', 'unknown')
                        sender = msg.get('senderName', 'Unknown')
                        text = msg.get('textMessage', '[No text]')
                        print(f"{i+1}. [{msg_type}] {sender}: {text[:50]}...")
            
            # Ask if the user wants to continue with the limited number of messages
            if not background_mode and not confirm_action("Continue with the limited number of messages?"):
                return None
            elif background_mode:
                print("\n🤖 Running in background mode - automatically continuing with limited messages")
        else:
            print(f"\n✅ Successfully processed {len(processed_messages)} messages for summarization")
            
        if len(processed_messages) == 0:
            display_error_and_continue("No valid messages after processing")
            return None
        
        # Store messages in the database if available
        if supabase_client:
            try:
                stored_count = supabase_client.store_messages(processed_messages, group_id)
                print(f"\n✅ Stored {stored_count} messages in database")
            except Exception as e:
                logger.warning(f"Could not store messages in database: {str(e)}")
                if debug:
                    print(f"\n⚠️ Database error: {str(e)}")
        
        # Filter messages by date if days parameter is specified
        if days > 0:
            # Calculate the start date (days ago)
            days_ago = datetime.now() - timedelta(days=days)
            print(f"\n📅 Filtering messages from the last {days} days (since {days_ago.strftime('%Y-%m-%d')})")
            
            # Filter messages
            filtered_messages = []
            total_messages = len(processed_messages)
            print("\nFiltering messages by date:")
            print("[" + "-" * 50 + "]")
            progress = 0
            
            for i, msg in enumerate(processed_messages):
                # Update progress bar every message
                new_progress = int((i + 1) / total_messages * 50)
                if new_progress > progress:
                    progress = new_progress
                    print("\r[" + "=" * progress + "-" * (50 - progress) + f"] {int((i + 1) / total_messages * 100)}%", end="", flush=True)
                
                if 'timestamp' in msg and msg['timestamp']:
                    try:
                        # Convert timestamp to datetime if it's a number
                        if isinstance(msg['timestamp'], (int, float)):
                            msg_time = datetime.fromtimestamp(msg['timestamp'])
                        # If it's already a datetime, use it as is
                        elif isinstance(msg['timestamp'], datetime):
                            msg_time = msg['timestamp']
                        else:
                            continue
                        
                        if msg_time >= days_ago:
                            filtered_messages.append(msg)
                    except:
                        continue
            
            print("\n")  # New line after progress bar
            print(f"✅ Filtered {len(filtered_messages)} messages from the last {days} days (out of {len(processed_messages)} total)")
            
            messages_for_summary = filtered_messages
        else:
            # Use all messages if no date filtering
            messages_for_summary = processed_messages
        
        # Add a cache-busting timestamp to ensure we get a fresh summary
        cache_buster = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # Option for custom prompt
        use_custom_prompt = debug and confirm_action("Would you like to use a custom prompt for the summary?")
        
        if use_custom_prompt:
            print("\nEnter your custom prompt instructions below (end with a blank line):")
            custom_instructions = []
            while True:
                line = input()
                if not line:
                    break
                custom_instructions.append(line)
            
            custom_prompt = "\n".join(custom_instructions)
            print(f"\n⏳ Generating summary with custom prompt ({len(custom_prompt)} chars)...")
            
            try:
                # Add cache buster to the custom prompt
                custom_prompt += f"\n\nTimestamp: {cache_buster}"
                summary = openai_client.generate_summary(messages_for_summary, custom_instructions=custom_instructions, target_language='hebrew')
                print(f"\n✅ Summary generated with custom prompt")
            except Exception as e:
                print(f"\n❌ Error generating summary with custom prompt: {str(e)}")
                if confirm_action("Try with default prompt instead?"):
                    print("\n⏳ Generating summary with default prompt...")
                    summary = openai_client.generate_summary(messages_for_summary, target_language='hebrew')
                else:
                    display_error_and_continue(f"Failed to generate summary: {str(e)}")
                    return None
        else:
            try:
                # Always force a new summary by using cache busting timestamp
                print("\n⏳ Generating fresh summary... הסיכום יהיה עדכני למועד הנוכחי")
                print("\nProcessing messages for summary:")
                print("[" + "-" * 50 + "]")
                
                # Initialize progress counter
                total_msgs = len(messages_for_summary)
                progress_step = max(1, total_msgs // 50)  # Update every 2%
                last_progress = 0
                
                def progress_callback(current, total):
                    nonlocal last_progress
                    progress = int(current / total * 50)
                    if progress > last_progress:
                        last_progress = progress
                        print("\r[" + "=" * progress + "-" * (50 - progress) + f"] {int(current / total * 100)}%", end="", flush=True)
                
                # Use the timestamp parameter for cache busting
                summary = openai_client.generate_summary(
                    messages_for_summary,
                    target_language='hebrew',
                    progress_callback=progress_callback
                )
                print("\n")  # New line after progress bar
                print(f"\n✅ Summary generated successfully")
                
                # Check summary quality by looking for too many "not reported" entries
                if "לא דווח" in summary and summary.count("לא דווח") > 10:
                    print("\n⚠️ התגלו יותר מדי רשומות 'לא דווח' בסיכום. זה עשוי להצביע על בעיה.")
                    if debug and confirm_action("האם לנסות ליצור סיכום חדש עם פחות סינון?"):
                        print("\n⏳ מנסה ליצור סיכום חדש עם פחות סינון...")
                        # Enable less filtering in the message processor if possible
                        if hasattr(message_processor, 'set_debug_mode'):
                            message_processor.set_debug_mode(True)
                            reprocessed_messages = message_processor.process_messages(messages)
                            if len(reprocessed_messages) > len(processed_messages):
                                print(f"\n✅ עיבוד מחדש מצא {len(reprocessed_messages)} הודעות (לעומת {len(processed_messages)} קודם)")
                                summary = openai_client.generate_summary(reprocessed_messages, target_language='hebrew')
                                print(f"\n✅ סיכום חדש נוצר בהצלחה")
                            else:
                                print("\n⚠️ עיבוד מחדש לא הניב יותר הודעות")
                
            except Exception as e:
                error_msg = str(e)
                print(f"\n❌ Error generating summary: {error_msg}")
                
                if "maximum context length" in error_msg.lower():
                    print("\nThe input might be too large for the model. Trying with fewer messages...")
                    # Try with half the messages
                    half_count = len(messages_for_summary) // 2
                    try:
                        reduced_messages = messages_for_summary[:half_count]
                        print(f"\n⏳ Retrying with {half_count} messages...")
                        summary = openai_client.generate_summary(reduced_messages, target_language='hebrew')
                        print(f"\n✅ Summary generated successfully with reduced message count")
                    except Exception as e2:
                        print(f"\n❌ Second attempt also failed: {str(e2)}")
                        display_error_and_continue(f"Failed to generate summary even with reduced messages: {str(e2)}")
                        return None
                else:
                    display_error_and_continue(f"Failed to generate summary: {error_msg}")
                    return None
        
        # Store the summary in the database if available
        if supabase_client:
            try:
                if messages_for_summary and len(messages_for_summary) > 0:
                    # חישוב תאריכי התחלה וסיום לסיכום בהתבסס על ההודעות המסוננות
                    timestamps = []
                    for msg in messages_for_summary:
                        if 'timestamp' in msg and msg['timestamp']:
                            try:
                                # נסה לפענח את החותמת בדרכים שונות
                                ts = msg['timestamp']
                                if isinstance(ts, str):
                                    if ts.isdigit():
                                        timestamps.append(int(ts))
                                    elif 'T' in ts:  # ISO format
                                        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                                        timestamps.append(dt.timestamp())
                                elif isinstance(ts, (int, float)):
                                    timestamps.append(ts)
                            except:
                                pass
                    
                    # חישוב התאריכים על סמך חותמות הזמן
                    start_time = datetime.fromtimestamp(min(timestamps)) if timestamps else datetime.now() - timedelta(days=days)
                    end_time = datetime.fromtimestamp(max(timestamps)) if timestamps else datetime.now()
                    
                    print(f"\n📅 Summary covers from {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}")
                else:
                    # אם אין הודעות מסוננות, השתמש בחישוב פשוט
                    end_time = datetime.now()
                    start_time = end_time - timedelta(days=days)
                    print(f"\n📅 Summary covers approximately {days} days (no message timestamps available)")
                
                # עיבוד רשימת המשתתפים
                participants = []
                participants_set = set()
                for msg in messages_for_summary:
                    sender = msg.get('senderName')
                    if sender and sender != 'Unknown' and sender not in participants_set:
                        participants_set.add(sender)
                        participants.append(sender)
                
                # שמירת הסיכום במסד הנתונים
                stored_summary = supabase_client.store_summary(
                    summary=summary,
                    group_id=group_id,
                    start_time=start_time,
                    end_time=end_time,
                    message_count=len(messages_for_summary),
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
        if debug:
            import traceback
            traceback.print_exc()
            print("\nTraceback printed for debugging")
        return None

def send_summary(components, group_id, summary, background_mode=False):
    """Send a summary to a WhatsApp group"""
    if not summary:
        print("\n❌ No summary to send")
        return False
        
    try:
        green_api_client = components.get('green_api_client')
        config_manager = components.get('config_manager')
        
        if not green_api_client:
            print("\n❌ Missing Green API client required for sending")
            return False
        
        # FORCE DISABLE MESSAGE SENDING - SAFETY MEASURE
        # This ensures messages are never sent accidentally during interactive mode
        # For background mode (scheduled tasks), allow sending messages
        message_sending_disabled = not background_mode
        
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

def auto_fetch_new_messages(components, group_id=None, background_mode=False):
    """Automatic fetching of new messages when starting the bot"""
    print("\n⏳ Automatically fetching new messages...")
    
    try:
        green_api_client = components.get('green_api_client')
        supabase_client = components.get('supabase_client')
        config_manager = components.get('config_manager')
        
        if not green_api_client or not supabase_client:
            print("❌ Missing required components for fetching messages")
            return False
        
        # Use specified group_id if provided, otherwise check for preferred/source group
        if not group_id:
            # Check if there is a preferred or source group defined
            group_id = os.environ.get('SOURCE_GROUP_ID', os.environ.get('PREFERRED_GROUP_ID'))
        
        if not group_id:
            # If no group specified, try to get the first group from the list
            try:
                group_manager = components.get('group_manager')
                if group_manager:
                    groups = group_manager.get_groups()
                    if groups and len(groups) > 0:
                        group_id = groups[0]['id']
                        print(f"⚠️ No group specified, using first group: {groups[0]['name']} ({group_id})")
            except Exception as e:
                error_msg = f"Error getting group list: {str(e)}"
                if background_mode:
                    print(f"⚠️ {error_msg} - continuing with limited functionality")
                    logging.getLogger(__name__).error(error_msg)
                else:
                    print(f"❌ {error_msg}")
                return False
        
        if not group_id:
            error_msg = "No group found for fetching messages"
            if background_mode:
                print(f"⚠️ {error_msg} - skipping message fetch")
                logging.getLogger(__name__).error(error_msg)
            else:
                print(f"❌ {error_msg}")
            return False
            
        print(f"📱 Fetching new messages from group: {group_id}")
        
        # Fetching new messages
        messages = green_api_client.get_chat_history(group_id, count=800, min_count=500)
        
        if not messages:
            error_msg = "No new messages received"
            if background_mode:
                print(f"⚠️ {error_msg} - continuing with existing database messages")
                logging.getLogger(__name__).warning(error_msg)
            else:
                print(f"❌ {error_msg}")
            return False
            
        print(f"✅ Received {len(messages)} new messages")
        
        # Storing messages in the database
        print("\n⏳ Storing messages in the database...")
        try:
            stored_count = supabase_client.store_messages(messages, group_id)
            print(f"✅ Stored {stored_count} new messages in the database")
        except Exception as db_error:
            error_msg = f"Error storing messages: {str(db_error)}"
            if background_mode:
                print(f"⚠️ {error_msg} - continuing with message processing")
                logging.getLogger(__name__).error(error_msg)
            else:
                print(f"❌ {error_msg}")
        
        return True
        
    except Exception as e:
        error_msg = f"Error in automatic message fetching: {str(e)}"
        if background_mode:
            print(f"⚠️ {error_msg} - attempting to continue")
            logging.getLogger(__name__).error(error_msg)
        else:
            print(f"❌ {error_msg}")
        return False

def background_menu(components):
    """Display the background mode menu and handle user interaction"""
    print_header("Background Mode")
    
    background_options = [
        {'key': '1', 'text': 'Start Bot in Background'},
        {'key': '2', 'text': 'Set Scheduled Posting Time'},
        {'key': '3', 'text': 'Set Source Group (for fetching messages)'},
        {'key': '4', 'text': 'Set Target Group (for posting summaries)'},
        {'key': '5', 'text': 'Set Test Group (for testing summaries)'},
        {'key': '6', 'text': 'View Current Background Settings'},
        {'key': '7', 'text': 'Back'}
    ]
    
    choice = show_menu("Background Mode", background_options, components)
    
    if choice == '1':
        # Start bot in background
        print_header("Start Bot in Background")
        print("\n⚠️ Running in background mode will keep the bot active and executing scheduled tasks.")
        print("⚠️ The terminal window must remain open while the bot is running.")
        
        if confirm_action("Start the bot in background mode?"):
            # Start the background bot
            bot = BackgroundBot()
            bot.start()
            
    elif choice == '2':
        # Set scheduled posting time
        print_header("Set Scheduled Posting Time")
        print("\nEnter the time when the bot should automatically post summaries (24-hour format).")
        print("Example: 08:00 for 8 AM, 18:30 for 6:30 PM")
        print("Leave empty to disable scheduled posting.")
        
        time_input = input("\nScheduled time (HH:MM): ").strip()
        
        if not time_input:
            # Disable scheduled posting
            save_user_setting('SCHEDULED_POST_TIME', '')
            print("\n✅ Scheduled posting disabled")
        else:
            # Validate time format
            try:
                hour, minute = time_input.split(':')
                hour, minute = int(hour), int(minute)
                
                if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                    print("\n❌ Invalid time format. Hours must be 0-23, minutes must be 0-59.")
                else:
                    time_str = f"{hour:02d}:{minute:02d}"
                    save_user_setting('SCHEDULED_POST_TIME', time_str)
                    print(f"\n✅ Scheduled posting time set to {time_str}")
            except ValueError:
                print("\n❌ Invalid time format. Please use HH:MM format.")
        
        input("\nPress Enter to continue...")
        
    elif choice == '3':
        # Set source group (for fetching messages)
        print_header("Set Source Group")
        print("\nSelect a group from which messages will be fetched for summary generation.")
        
        if 'group_manager' not in components:
            display_error_and_continue("Group manager not available")
            return
        
        group = select_group(components)
        if group:
            # Save source group ID to user settings
            save_user_setting('SOURCE_GROUP_ID', group['id'])
            print(f"\n✅ Source group set to: {group['name']}")
            input("\nPress Enter to continue...")
            
    elif choice == '4':
        # Set target group (for posting summaries)
        print_header("Set Target Group")
        print("\nSelect a group where summaries will be posted.")
        print("Leave this unset to use the source group for posting.")
        
        if 'group_manager' not in components:
            display_error_and_continue("Group manager not available")
            return
        
        print("\nCurrent groups:")
        groups = components['group_manager'].get_groups()
        for i, group in enumerate(groups, 1):
            print(f"{i}. {group['name']} ({group['id']})")
        
        print("\n0. Clear target group (use source group instead)")
        print("C. Cancel")
        
        group_choice = input("\nSelect group: ").strip()
        
        if group_choice.lower() == 'c':
            return
        elif group_choice == '0':
            save_user_setting('TARGET_GROUP_ID', '')
            print("\n✅ Target group cleared. Source group will be used for posting.")
        else:
            try:
                group_index = int(group_choice) - 1
                if 0 <= group_index < len(groups):
                    selected_group = groups[group_index]
                    save_user_setting('TARGET_GROUP_ID', selected_group['id'])
                    print(f"\n✅ Target group set to: {selected_group['name']}")
                else:
                    print("\n❌ Invalid selection.")
            except ValueError:
                print("\n❌ Invalid input. Please enter a number.")
        
        input("\nPress Enter to continue...")
        
    elif choice == '5':
        # Set test group
        print_header("Set Test Group")
        print("\nSelect a group where test summaries will be sent during testing.")
        print("This overrides both source and target groups for posting.")
        print("Leave this unset to use the target/source group configuration.")
        
        if 'group_manager' not in components:
            display_error_and_continue("Group manager not available")
            return
        
        print("\nCurrent groups:")
        groups = components['group_manager'].get_groups()
        for i, group in enumerate(groups, 1):
            print(f"{i}. {group['name']} ({group['id']})")
        
        print("\n0. Clear test group")
        print("C. Cancel")
        
        group_choice = input("\nSelect group: ").strip()
        
        if group_choice.lower() == 'c':
            return
        elif group_choice == '0':
            save_user_setting('TEST_GROUP_ID', '')
            print("\n✅ Test group cleared.")
        else:
            try:
                group_index = int(group_choice) - 1
                if 0 <= group_index < len(groups):
                    selected_group = groups[group_index]
                    save_user_setting('TEST_GROUP_ID', selected_group['id'])
                    print(f"\n✅ Test group set to: {selected_group['name']}")
                else:
                    print("\n❌ Invalid selection.")
            except ValueError:
                print("\n❌ Invalid input. Please enter a number.")
        
        input("\nPress Enter to continue...")
        
    elif choice == '6':
        # View current background settings
        print_header("Current Background Settings")
        
        # Load user settings
        user_settings = {}
        try:
            if os.path.exists('user_settings.json'):
                with open('user_settings.json', 'r') as f:
                    user_settings = json.load(f)
        except Exception as e:
            print(f"❌ Error loading user settings: {str(e)}")
        
        # Display relevant settings
        print("Background Mode Settings:")
        
        # Scheduled posting time
        scheduled_time = user_settings.get('SCHEDULED_POST_TIME', os.environ.get('SCHEDULED_POST_TIME', 'Not set'))
        print(f"  Scheduled Posting Time: {scheduled_time if scheduled_time else 'Disabled'}")
        
        # Get group manager for showing names
        group_manager = components.get('group_manager')
        groups = []
        if group_manager:
            try:
                groups = group_manager.get_groups()
            except Exception:
                pass
        
        # Helper function to get group name from ID
        def get_group_name(group_id):
            if not group_id or group_id == 'Not set':
                return 'Not set'
            
            for group in groups:
                if group['id'] == group_id:
                    return group['name']
            return 'Unknown'
        
        # Source group
        source_group_id = user_settings.get('SOURCE_GROUP_ID', os.environ.get('SOURCE_GROUP_ID', 
                          user_settings.get('PREFERRED_GROUP_ID', os.environ.get('PREFERRED_GROUP_ID', 'Not set'))))
        source_group_name = get_group_name(source_group_id)
        print(f"  Source Group: {source_group_id} ({source_group_name})")
        
        # Target group
        target_group_id = user_settings.get('TARGET_GROUP_ID', os.environ.get('TARGET_GROUP_ID', 'Not set'))
        if target_group_id and target_group_id != 'Not set':
            target_group_name = get_group_name(target_group_id)
            print(f"  Target Group: {target_group_id} ({target_group_name})")
        else:
            print(f"  Target Group: Not set (using Source Group)")
        
        # Test group
        test_group_id = user_settings.get('TEST_GROUP_ID', os.environ.get('TEST_GROUP_ID', 'Not set'))
        if test_group_id and test_group_id != 'Not set':
            test_group_name = get_group_name(test_group_id)
            print(f"  Test Group: {test_group_id} ({test_group_name})")
        else:
            print(f"  Test Group: Not set")
        
        # Summary flow explanation
        print("\nSummary Posting Flow:")
        if test_group_id and test_group_id != 'Not set':
            print(f"  Messages from: {source_group_name}")
            print(f"  Summaries to: {get_group_name(test_group_id)} (Test Group)")
        elif target_group_id and target_group_id != 'Not set':
            print(f"  Messages from: {source_group_name}")
            print(f"  Summaries to: {get_group_name(target_group_id)} (Target Group)")
        else:
            print(f"  Messages from: {source_group_name}")
            print(f"  Summaries to: {source_group_name} (Source Group)")
        
        input("\nPress Enter to continue...")
        
    elif choice == '7':
        # Back to main menu
        return

def run_main_menu():
    """Display the main menu and handle user interaction"""
    # Initialize components
    print("⏳ Initializing components...")
    components = initialize_components()
    
    # Remove automatic message fetching on startup
    print("\n===============================")
    print("📋 Welcome to the main menu")
    print("===============================\n")
    
    # Define main menu options
    main_menu_options = [
        {'key': '1', 'text': 'Generate New Summary', 'requires': ['group_manager', 'openai_client']},
        {'key': '2', 'text': 'Fetch New Messages', 'requires': ['green_api_client', 'supabase_client']},
        {'key': '3', 'text': 'Background Mode', 'requires': ['green_api_client', 'supabase_client', 'openai_client']},
        {'key': '4', 'text': 'Settings'},
        {'key': '5', 'text': 'Debug Mode'},
        {'key': '6', 'text': 'Exit'}
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
            # Fetch New Messages
            fetch_result = auto_fetch_new_messages(components)
            if fetch_result:
                print("\n✅ Messages fetched and stored successfully")
            else:
                print("\n⚠️ Failed to fetch messages or no new messages available")
            
            input("\nPress Enter to continue...")
            
        elif choice == '3':
            # Background Mode
            background_menu(components)
            
        elif choice == '4':
            # Settings
            settings_menu(components)
            
        elif choice == '5':
            # Debug Mode
            debug_menu(components)
            
        elif choice == '6':
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
    
    Background Mode:
    - To run in background: python summary_menu_new.py --background
    - The bot can be scheduled to post at specific times
    """
    # Handle command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == '--background':
        # Run in background mode
        print("Starting bot in background mode...")
        bot = BackgroundBot()
        try:
            bot.start()
        except KeyboardInterrupt:
            print("\n\nProgram terminated by user.")
        except Exception as e:
            logger.error(f"Unexpected error in background mode: {str(e)}")
            print(f"\n\nAn unexpected error occurred: {str(e)}")
    else:
        # Run in interactive mode
        try:
            run_main_menu()
        except KeyboardInterrupt:
            print("\n\nProgram terminated by user.")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            print(f"\n\nAn unexpected error occurred: {str(e)}")
        
    print("\nGoodbye!") 