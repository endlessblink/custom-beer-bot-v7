#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WhatsApp Message Fetcher

This script fetches new messages from WhatsApp and stores them in the database.
It can be run manually whenever you want to update the database with fresh messages.
"""

import os
import sys
import logging
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv(override=True)

# Import project components
from green_api.client import GreenAPIClient
from db.supabase_client import SupabaseClient
from processor.message_processor import MessageProcessor
from config.config_manager import ConfigManager
from utils.logger import setup_logger

# Configure logging
logger = setup_logger("INFO")

def main():
    """Fetch new messages and store them in the database"""
    print("\n==== WhatsApp Message Fetcher ====\n")
    
    # Load configuration
    config_manager = ConfigManager()
    
    # Initialize components
    try:
        print("1. Initializing components...")
        
        green_api_client = GreenAPIClient(
            instance_id=os.environ.get('GREEN_API_ID_INSTANCE'),
            instance_token=os.environ.get('GREEN_API_TOKEN')
        )
        
        supabase_client = SupabaseClient(
            url=os.environ.get('SUPABASE_URL'),
            key=os.environ.get('SUPABASE_KEY')
        )
        
        message_processor = MessageProcessor()
        
        print("✅ All components initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize components: {str(e)}")
        return
    
    # Get active group ID
    group_id = config_manager.get('ACTIVE_GROUP_ID')
    if not group_id:
        # Check env file for group IDs
        env_group_ids = os.environ.get('WHATSAPP_GROUP_IDS', '')
        if env_group_ids:
            # Split by comma in case multiple IDs are defined
            group_ids = [gid.strip() for gid in env_group_ids.split(',')]
            if group_ids:
                if len(group_ids) == 1:
                    group_id = group_ids[0]
                    print(f"\n2. Using group ID from environment: {group_id}")
                    # Save for future use
                    config_manager.set('ACTIVE_GROUP_ID', group_id)
                else:
                    print("\n2. Multiple group IDs found in environment:")
                    for i, gid in enumerate(group_ids):
                        print(f"{i+1}. {gid}")
                    try:
                        choice = input("\nSelect a group number: ")
                        index = int(choice) - 1
                        if 0 <= index < len(group_ids):
                            group_id = group_ids[index]
                            # Save for future use
                            config_manager.set('ACTIVE_GROUP_ID', group_id)
                            print(f"✅ Selected group ID: {group_id}")
                        else:
                            print("❌ Invalid selection")
                            return
                    except (ValueError, IndexError):
                        print("❌ Invalid selection")
                        return
        
        # If still no group ID, ask for manual input
        if not group_id:
            print("\n2. No group ID found. Please enter manually.")
            print("   Tip: Check the .env file for WHATSAPP_GROUP_IDS value")
            group_id = input("\nGroup ID: ")
            if not group_id:
                print("❌ No group ID provided")
                return
            
            # Save for future use
            config_manager.set('ACTIVE_GROUP_ID', group_id)
            print(f"✅ Group ID set to: {group_id}")
    else:
        print(f"\n2. Using configured group ID: {group_id}")
    
    # Get latest message from database
    print("\n3. Checking database for latest message timestamp...")
    latest_timestamp = None
    
    try:
        result = supabase_client.client.table('messages').select('timestamp').eq('group_id', group_id).order('timestamp', desc=True).limit(1).execute()
        
        if result.data and len(result.data) > 0:
            latest_timestamp = result.data[0].get('timestamp')
            
            # Convert to datetime if it's a string
            if isinstance(latest_timestamp, str):
                try:
                    latest_timestamp = datetime.fromisoformat(latest_timestamp.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        latest_timestamp = datetime.strptime(latest_timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
                        # Add timezone info
                        latest_timestamp = latest_timestamp.replace(tzinfo=timezone.utc)
                    except ValueError:
                        latest_timestamp = None
            
            if latest_timestamp:
                print(f"✅ Latest message in database is from: {latest_timestamp}")
                
                # Calculate time difference - make sure both datetimes have timezone info
                now = datetime.now(timezone.utc)  # Current time with UTC timezone
                days_since = (now - latest_timestamp).days
                print(f"   Days since last message: {days_since}")
            else:
                print("⚠️ Could not determine latest message timestamp")
        else:
            print("ℹ️ No messages found in database for this group")
    except Exception as e:
        print(f"❌ Error checking database: {str(e)}")
        latest_timestamp = None  # Reset if there was an error
    
    # Fetch messages from WhatsApp
    print("\n4. Fetching messages from WhatsApp...")
    
    # Determine how many messages to fetch based on latest timestamp
    count = 100
    if latest_timestamp:
        try:
            now = datetime.now(timezone.utc)
            days_since = (now - latest_timestamp).days
            if days_since > 7:
                count = 500  # Fetch more messages if it's been a while
                print(f"ℹ️ Increasing fetch count to {count} due to {days_since} days since last message")
        except Exception as e:
            print(f"⚠️ Error calculating days since last message: {str(e)}. Using default count.")
    
    try:
        print(f"ℹ️ Requesting {count} messages with minimum of {count//2}...")
        messages = green_api_client.get_chat_history(group_id, count=count, min_count=count//2)
        
        if messages and len(messages) > 0:
            print(f"✅ Successfully fetched {len(messages)} messages from WhatsApp")
            
            # Process the messages
            print("\n5. Processing messages...")
            processed_messages = message_processor.process_messages(messages)
            print(f"✅ Processed {len(processed_messages)} messages")
            
            # Find messages newer than the latest in the database
            new_messages = []
            if latest_timestamp:
                for msg in processed_messages:
                    if 'timestamp' in msg and msg['timestamp']:
                        msg_timestamp = msg['timestamp']
                        
                        # Convert to datetime if needed
                        try:
                            if isinstance(msg_timestamp, (int, float)):
                                msg_datetime = datetime.fromtimestamp(msg_timestamp, tz=timezone.utc)
                            elif isinstance(msg_timestamp, str) and msg_timestamp.isdigit():
                                msg_datetime = datetime.fromtimestamp(int(msg_timestamp), tz=timezone.utc)
                            else:
                                # Skip messages with invalid timestamps
                                continue
                            
                            # Check if newer than latest
                            if msg_datetime > latest_timestamp:
                                new_messages.append(msg)
                        except Exception as dt_error:
                            print(f"⚠️ Error processing timestamp for message: {str(dt_error)}")
                            continue
                
                print(f"ℹ️ Found {len(new_messages)} new messages since {latest_timestamp}")
            else:
                # If no latest timestamp, consider all messages as new
                new_messages = processed_messages
                print(f"ℹ️ No previous messages in database, considering all {len(new_messages)} as new")
            
            # Store in database
            if new_messages:
                print("\n6. Storing new messages in database...")
                try:
                    stored_count = supabase_client.store_messages(new_messages, group_id)
                    print(f"✅ Successfully stored {stored_count} new messages in database")
                except Exception as e:
                    print(f"❌ Error storing messages: {str(e)}")
            else:
                print("\n6. No new messages to store in database")
        else:
            print("❌ No messages returned from WhatsApp API")
    except Exception as e:
        print(f"❌ Error fetching messages: {str(e)}")
    
    print("\n==== Message Fetch Completed ====")

if __name__ == "__main__":
    main() 