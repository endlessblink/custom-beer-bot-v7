#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Debug Menu Module

This module provides debugging tools and information.
"""

import os
import logging
import json
import time
from datetime import datetime
from utils.menu.core_menu import show_menu, display_error_and_continue

logger = logging.getLogger("whatsapp_bot")

def debug_menu(components):
    """
    Display debugging options and information
    
    Args:
        components (dict): Dictionary of initialized components
    """
    while True:
        try:
            options = [
                {'key': '1', 'text': 'View Environment Variables'},
                {'key': '2', 'text': 'Test Database Connection'},
                {'key': '3', 'text': 'View Message Counts'},
                {'key': '4', 'text': 'View Recent Summaries'},
                {'key': '5', 'text': 'Back to Main Menu'}
            ]
            
            choice = show_menu("Debug Menu", options)
            
            if choice == '1':
                # View environment variables (sensitive info redacted)
                view_environment_variables()
                input("\nPress Enter to continue...")
                
            elif choice == '2':
                # Test database connection
                test_database_connection(components)
                input("\nPress Enter to continue...")
                
            elif choice == '3':
                # View message counts
                view_message_counts(components)
                input("\nPress Enter to continue...")
                
            elif choice == '4':
                # View recent summaries
                view_recent_summaries(components)
                input("\nPress Enter to continue...")
                
            elif choice == '5':
                # Return to main menu
                return
                
        except Exception as e:
            logger.error(f"Error in debug menu: {str(e)}", exc_info=True)
            display_error_and_continue(f"Error: {str(e)}")

def view_environment_variables():
    """
    Display environment variables with sensitive information redacted
    """
    try:
        print("\nEnvironment Variables:")
        
        # List of sensitive variables to redact
        sensitive_vars = [
            'API_KEY', 'KEY', 'TOKEN', 'SECRET', 'PASSWORD', 'PASS', 'PWD'
        ]
        
        # Get all environment variables
        for key, value in sorted(os.environ.items()):
            # Skip system variables
            if key.startswith('_') or key.startswith('ALLUSERS') or key.startswith('APPDATA'):
                continue
                
            # Redact sensitive information
            is_sensitive = any(s in key.upper() for s in sensitive_vars)
            display_value = value
            
            if is_sensitive and value:
                # Redact all but first and last 2 characters
                if len(value) > 6:
                    display_value = value[:2] + '*' * (len(value) - 4) + value[-2:]
                else:
                    display_value = '*' * len(value)
                    
            print(f"{key}: {display_value}")
            
    except Exception as e:
        logger.error(f"Error viewing environment variables: {str(e)}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")

def test_database_connection(components):
    """
    Test database connection and display results
    
    Args:
        components (dict): Dictionary of initialized components
    """
    try:
        print("\nTesting database connection...")
        
        # Get Supabase client
        supabase_client = components.get('supabase_client')
        if not supabase_client:
            print("\n❌ Supabase client not found in components")
            return
            
        # Test connection
        print("Connecting to database...")
        start_time = time.time()
        
        try:
            # Try different methods to query the database
            try:
                result = supabase_client.client.table('messages').select('count', count='exact').limit(1).execute()
                print(f"✅ Connection successful using client.table method")
            except Exception as e1:
                print(f"❌ First method failed: {str(e1)}")
                try:
                    result = supabase_client.table('messages').select('count', count='exact').limit(1).execute()
                    print(f"✅ Connection successful using table method")
                except Exception as e2:
                    print(f"❌ Second method failed: {str(e2)}")
                    result = supabase_client.client.from_('messages').select('count', count='exact').limit(1).execute()
                    print(f"✅ Connection successful using from_ method")
                
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"Connection test completed in {duration:.2f} seconds")
            
            # Get table counts
            print("\nTable Counts:")
            tables = ['messages', 'summaries', 'groups', 'user_expertise']
            
            for table in tables:
                try:
                    # Try different methods
                    try:
                        count_result = supabase_client.client.table(table).select('count', count='exact').execute()
                        count = count_result.count
                    except:
                        try:
                            count_result = supabase_client.table(table).select('count', count='exact').execute()
                            count = count_result.count
                        except:
                            count_result = supabase_client.client.from_(table).select('count', count='exact').execute()
                            count = count_result.count
                            
                    print(f"- {table}: {count} rows")
                except Exception as e:
                    print(f"- {table}: Error getting count - {str(e)}")
                
        except Exception as e:
            print(f"\n❌ Connection test failed: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error testing database connection: {str(e)}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")

def view_message_counts(components):
    """
    Display message counts by group and date
    
    Args:
        components (dict): Dictionary of initialized components
    """
    try:
        print("\nMessage Counts:")
        
        # Get Supabase client
        supabase_client = components.get('supabase_client')
        if not supabase_client:
            print("\n❌ Supabase client not found in components")
            return
            
        # Try different methods to query for message counts per group
        try:
            # Try to get messages grouped by group_id with count
            try:
                result = supabase_client.client.table('messages').select('group_id, count').execute()
                groups_data = result.data
            except Exception as e1:
                print(f"Query method 1 failed: {str(e1)}")
                try:
                    result = supabase_client.table('messages').select('group_id, count').execute()  
                    groups_data = result.data
                except Exception as e2:
                    print(f"Query method 2 failed: {str(e2)}")
                    # Fallback to manual counting
                    print("Falling back to manual counting...")
                    result = supabase_client.client.table('messages').select('group_id').execute()
                    messages = result.data
                    
                    # Count messages by group
                    group_counts = {}
                    for msg in messages:
                        group_id = msg.get('group_id')
                        if group_id:
                            if group_id in group_counts:
                                group_counts[group_id] += 1
                            else:
                                group_counts[group_id] = 1
                                
                    groups_data = [{'group_id': k, 'count': v} for k, v in group_counts.items()]
            
            # Fetch group names if available
            group_names = {}
            try:
                groups_result = supabase_client.client.table('groups').select('id, name').execute()
                for group in groups_result.data:
                    group_names[group.get('id')] = group.get('name')
            except Exception as e:
                print(f"Could not fetch group names: {str(e)}")
            
            # Display counts
            if groups_data:
                print("\nCounts by Group:")
                for item in groups_data:
                    group_id = item.get('group_id')
                    count = item.get('count', 0)
                    group_name = group_names.get(group_id, 'Unknown')
                    print(f"- {group_name} ({group_id}): {count} messages")
            else:
                print("No message count data available")
                
            # Get recent messages
            print("\nMost Recent Messages:")
            try:
                recent_result = supabase_client.client.table('messages').select('*').order('timestamp', desc=True).limit(5).execute()
                recent_messages = recent_result.data
                
                for msg in recent_messages:
                    timestamp = msg.get('timestamp', 'Unknown')
                    sender = msg.get('sender', 'Unknown')
                    content = msg.get('content', '')
                    if len(content) > 50:
                        content = content[:50] + "..."
                    print(f"- [{timestamp}] {sender}: {content}")
            except Exception as e:
                print(f"Could not fetch recent messages: {str(e)}")
                
        except Exception as e:
            print(f"\n❌ Error querying messages: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error viewing message counts: {str(e)}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")

def view_recent_summaries(components):
    """
    Display recent summaries from the database
    
    Args:
        components (dict): Dictionary of initialized components
    """
    try:
        print("\nRecent Summaries:")
        
        # Get Supabase client
        supabase_client = components.get('supabase_client')
        if not supabase_client:
            print("\n❌ Supabase client not found in components")
            return
            
        # Try different methods to query for recent summaries
        try:
            try:
                result = supabase_client.client.table('summaries').select('*').order('generated_at', desc=True).limit(3).execute()
                summaries = result.data
            except Exception as e1:
                print(f"Query method 1 failed: {str(e1)}")
                try:
                    result = supabase_client.table('summaries').select('*').order('generated_at', desc=True).limit(3).execute()
                    summaries = result.data
                except Exception as e2:
                    print(f"Query method 2 failed: {str(e2)}")
                    result = supabase_client.client.from_('summaries').select('*').order('generated_at', desc=True).limit(3).execute()
                    summaries = result.data
            
            if summaries:
                for idx, summary in enumerate(summaries):
                    gen_time = summary.get('generated_at', 'Unknown')
                    group_id = summary.get('group_id', 'Unknown')
                    content = summary.get('content', '')
                    message_count = summary.get('message_count', 0)
                    status = summary.get('status', 'Unknown')
                    
                    print(f"\nSummary #{idx+1}:")
                    print(f"Generated: {gen_time}")
                    print(f"Group: {group_id}")
                    print(f"Message Count: {message_count}")
                    print(f"Status: {status}")
                    print(f"Preview: {content[:150]}..." if len(content) > 150 else f"Preview: {content}")
                    print("-" * 40)
            else:
                print("No summaries found in database")
                
        except Exception as e:
            print(f"\n❌ Error querying summaries: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error viewing recent summaries: {str(e)}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")
        
if __name__ == "__main__":
    # Test environment variables function
    view_environment_variables() 