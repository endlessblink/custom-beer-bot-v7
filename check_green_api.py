#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Green API Connection Checker

This script checks the connection to the Green API and attempts to fetch recent messages.
It also checks the latest messages in the database for comparison.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv(override=True)

# Import project components
from green_api.client import GreenAPIClient
from db.supabase_client import SupabaseClient
from config.config_manager import ConfigManager

def main():
    """Check the Green API connection and fetch recent messages"""
    print("\n==== Green API Connection Checker ====\n")
    
    # Load configuration
    config_manager = ConfigManager()
    
    # Initialize API client
    try:
        print("1. Initializing Green API client...")
        green_api_client = GreenAPIClient(
            instance_id=os.environ.get('GREEN_API_ID_INSTANCE'),
            instance_token=os.environ.get('GREEN_API_TOKEN')
        )
        print("✅ Green API client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Green API client: {str(e)}")
        return
    
    # Initialize Supabase client
    try:
        print("\n2. Initializing Supabase client...")
        supabase_client = SupabaseClient(
            url=os.environ.get('SUPABASE_URL'),
            key=os.environ.get('SUPABASE_KEY')
        )
        print("✅ Supabase client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Supabase client: {str(e)}")
        return
    
    # Get active group ID
    group_id = config_manager.get('ACTIVE_GROUP_ID')
    if not group_id:
        print("\n❌ No active group ID found in configuration")
        print("Please run the bot once to set the active group ID")
        return
    
    print(f"\n3. Checking database for latest messages for group {group_id}...")
    try:
        # Query database for latest message timestamp
        result = supabase_client.client.table('messages').select('timestamp').eq('group_id', group_id).order('timestamp', desc=True).limit(1).execute()
        
        if result.data and len(result.data) > 0:
            latest_timestamp = result.data[0].get('timestamp')
            print(f"✅ Latest message in database is from: {latest_timestamp}")
            
            # Convert to datetime if it's a string
            if isinstance(latest_timestamp, str):
                try:
                    latest_timestamp = datetime.fromisoformat(latest_timestamp.replace('Z', '+00:00'))
                except ValueError:
                    # Try other format
                    try:
                        latest_timestamp = datetime.strptime(latest_timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
                    except ValueError:
                        print(f"⚠️ Could not parse timestamp format: {latest_timestamp}")
            
            # Calculate days since last message
            if isinstance(latest_timestamp, datetime):
                days_since = (datetime.now() - latest_timestamp).days
                print(f"   Days since last message: {days_since}")
                
                if days_since > 1:
                    print(f"⚠️ No messages have been stored for {days_since} days!")
        else:
            print("⚠️ No messages found in database for this group")
    except Exception as e:
        print(f"❌ Error checking database: {str(e)}")
    
    # Check last summary
    print("\n4. Checking database for latest summary...")
    try:
        result = supabase_client.client.table('summaries').select('created_at, message_count').order('created_at', desc=True).limit(1).execute()
        
        if result.data and len(result.data) > 0:
            latest_summary = result.data[0]
            print(f"✅ Latest summary created at: {latest_summary.get('created_at')}")
            print(f"   Message count: {latest_summary.get('message_count')}")
            
            created_at = latest_summary.get('created_at')
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        created_at = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%S.%fZ')
                    except ValueError:
                        print(f"⚠️ Could not parse timestamp format: {created_at}")
            
            if isinstance(created_at, datetime):
                days_since = (datetime.now() - created_at).days
                print(f"   Days since last summary: {days_since}")
                
                if days_since > 1:
                    print(f"⚠️ No summary has been created for {days_since} days!")
        else:
            print("⚠️ No summaries found in database")
    except Exception as e:
        print(f"❌ Error checking summaries: {str(e)}")
    
    # Attempt to fetch new messages
    print("\n5. Attempting to fetch new messages from Green API...")
    try:
        messages = green_api_client.get_chat_history(group_id, count=50)
        
        if messages and len(messages) > 0:
            print(f"✅ Successfully fetched {len(messages)} messages from Green API")
            
            # Check timestamps
            timestamps = []
            for msg in messages:
                if 'timestamp' in msg and msg['timestamp'] is not None:
                    timestamp = msg['timestamp']
                    
                    # Convert to datetime if possible
                    if isinstance(timestamp, (int, float)):
                        timestamp = datetime.fromtimestamp(timestamp)
                    elif isinstance(timestamp, str):
                        try:
                            timestamp = int(timestamp)
                            timestamp = datetime.fromtimestamp(timestamp)
                        except (ValueError, TypeError):
                            # Leave as is if not convertible
                            pass
                    
                    timestamps.append(timestamp)
            
            if timestamps:
                # Sort timestamps
                try:
                    timestamps.sort()
                    oldest = timestamps[0]
                    newest = timestamps[-1]
                    
                    print(f"   Oldest message timestamp: {oldest}")
                    print(f"   Newest message timestamp: {newest}")
                    
                    # Check if these are newer than what's in the database
                    if isinstance(newest, datetime) and isinstance(latest_timestamp, datetime):
                        if newest > latest_timestamp:
                            print(f"✅ Found {len([t for t in timestamps if t > latest_timestamp])} new messages not yet in database!")
                        else:
                            print("⚠️ No new messages found that aren't already in the database")
                except Exception as sort_error:
                    print(f"⚠️ Error analyzing timestamps: {str(sort_error)}")
            else:
                print("⚠️ No timestamps found in messages")
            
            # Print the first message as example
            try:
                first_msg = messages[0]
                print("\nExample message (first in list):")
                sender = first_msg.get('senderName', 'Unknown')
                timestamp = first_msg.get('timestamp', 'Unknown time')
                text = first_msg.get('textMessage', '(no text)')
                print(f"   From: {sender}")
                print(f"   Time: {timestamp}")
                print(f"   Text: {text[:100]}...")
            except Exception as msg_error:
                print(f"⚠️ Error printing example message: {str(msg_error)}")
        else:
            print("❌ No messages returned from Green API")
    except Exception as e:
        print(f"❌ Error fetching messages from Green API: {str(e)}")
    
    # Check for webhook issues
    print("\n6. Checking webhook configuration...")
    try:
        webhooks = green_api_client.get_available_webhooks()
        print(f"Available webhooks: {json.dumps(webhooks, indent=2)}")
        
        # Check if webhook URL is set correctly
        webhook_url = webhooks.get('webhookUrl', '')
        if not webhook_url:
            print("⚠️ No webhook URL configured - this is required for receiving new messages automatically!")
        else:
            print(f"✅ Webhook URL is configured: {webhook_url}")
    except Exception as e:
        print(f"❌ Error checking webhooks: {str(e)}")
    
    print("\n==== Check Completed ====")

if __name__ == "__main__":
    main() 