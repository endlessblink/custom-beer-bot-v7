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
                {'key': '1', 'text': 'Check Services Status'},
                {'key': '2', 'text': 'View Environment Variables'},
                {'key': '3', 'text': 'Test Database Connection'},
                {'key': '4', 'text': 'View Message Counts'},
                {'key': '5', 'text': 'View Recent Summaries'},
                {'key': '6', 'text': 'Deep Inspect WhatsApp API Client'},
                {'key': '7', 'text': 'Back to Main Menu'}
            ]
            
            choice = show_menu("Debug Menu", options)
            
            if choice == '1':
                # Check status of all services
                check_services_status(components)
                input("\nPress Enter to continue...")
                
            elif choice == '2':
                # View environment variables (sensitive info redacted)
                view_environment_variables()
                input("\nPress Enter to continue...")
                
            elif choice == '3':
                # Test database connection
                test_database_connection(components)
                input("\nPress Enter to continue...")
                
            elif choice == '4':
                # View message counts
                view_message_counts(components)
                input("\nPress Enter to continue...")
                
            elif choice == '5':
                # View recent summaries
                view_recent_summaries(components)
                input("\nPress Enter to continue...")
            
            elif choice == '6':
                # Deep inspect WhatsApp API client
                deep_inspect_whatsapp_client(components)
                input("\nPress Enter to continue...")
                
            elif choice == '7':
                # Return to main menu
                return
                
        except Exception as e:
            logger.error(f"Error in debug menu: {str(e)}", exc_info=True)
            display_error_and_continue(f"Error: {str(e)}")

def check_services_status(components):
    """
    Check the status of all services and display the results
    
    Args:
        components (dict): Dictionary of initialized components
    """
    try:
        print("\n🔍 Checking services status...\n")
        print("Services Status:")
        print("-" * 50)
        
        status_checks = []
        
        # Check Green API (WhatsApp)
        try:
            green_api = components.get('green_api_client')
            if not green_api:
                status_checks.append(("WhatsApp API Client", False, "Component not initialized"))
            else:
                # Updated check based on deep inspection results
                green_api_working = False
                
                # Check for the exact attributes discovered in deep inspection
                has_instance_id = hasattr(green_api, 'instance_id')
                has_instance_token = hasattr(green_api, 'instance_token')
                has_base_url = hasattr(green_api, 'base_url')
                
                # Check for the specific methods discovered in deep inspection
                has_send_message = hasattr(green_api, 'send_message') and callable(getattr(green_api, 'send_message'))
                has_get_contacts = hasattr(green_api, 'get_contacts') and callable(getattr(green_api, 'get_contacts'))
                has_get_instance_status = hasattr(green_api, 'get_instance_status') and callable(getattr(green_api, 'get_instance_status'))
                
                # Define what methods we found
                methods_found = []
                if has_send_message:
                    methods_found.append('send_message')
                if has_get_contacts:
                    methods_found.append('get_contacts')
                if has_get_instance_status:
                    methods_found.append('get_instance_status')
                
                # Determine if the client is properly initialized
                if has_instance_id and has_instance_token and has_base_url:
                    instance_id = getattr(green_api, 'instance_id')
                    base_url = getattr(green_api, 'base_url')
                    status_checks.append((
                        "WhatsApp API (Green API)", 
                        True, 
                        f"Initialized with ID: {instance_id}, URL: {base_url}"
                    ))
                    green_api_working = True
                elif len(methods_found) > 0:
                    # At least some methods are available
                    status_message = f"Partially initialized with methods: {', '.join(methods_found)}"
                    status_checks.append(("WhatsApp API (Green API)", True, status_message))
                    green_api_working = True
                else:
                    # Last resort - check if any public methods/attributes exist
                    all_attrs = [a for a in dir(green_api) if not a.startswith('_')]
                    methods = [a for a in all_attrs if callable(getattr(green_api, a))]
                    
                    if methods:
                        status_message = f"Found {len(methods)} methods, but missing core attributes"
                        status_checks.append(("WhatsApp API (Green API)", True, status_message))
                        green_api_working = True
                    else:
                        status_checks.append(("WhatsApp API (Green API)", False, "Missing required attributes and methods"))
                        
        except Exception as e:
            status_checks.append(("WhatsApp API (Green API)", False, str(e)))
            
        # Check Group Manager
        try:
            group_manager = components.get('group_manager')
            if not group_manager:
                status_checks.append(("Group Manager", False, "Component not initialized"))
            else:
                # Try to get groups
                try:
                    groups = group_manager.get_groups()
                    if isinstance(groups, list):
                        status_checks.append(("Group Manager", True, f"Found {len(groups)} groups"))
                    else:
                        status_checks.append(("Group Manager", False, "Invalid response"))
                except Exception as e:
                    status_checks.append(("Group Manager", False, str(e)))
        except Exception as e:
            status_checks.append(("Group Manager", False, str(e)))
            
        # Check OpenAI
        try:
            openai_client = components.get('openai_client')
            if not openai_client:
                status_checks.append(("OpenAI API", False, "Component not initialized"))
            else:
                # Check if API key is set - don't try to call test_connection
                if hasattr(openai_client, 'api_key') and openai_client.api_key:
                    try:
                        # Just check if the client is properly initialized with required attributes
                        if hasattr(openai_client, 'model'):
                            status_checks.append(("OpenAI API", True, f"Initialized with model: {openai_client.model}"))
                        else:
                            status_checks.append(("OpenAI API", True, "API key set, but model not specified"))
                    except Exception as e:
                        status_checks.append(("OpenAI API", False, str(e)))
                else:
                    status_checks.append(("OpenAI API", False, "No API key set"))
        except Exception as e:
            status_checks.append(("OpenAI API", False, str(e)))
            
        # Check Supabase
        try:
            supabase_client = components.get('supabase_client')
            if not supabase_client:
                status_checks.append(("Supabase Database", False, "Component not initialized"))
            else:
                # Try different methods to query the database
                try:
                    # Try a simple query
                    try:
                        result = supabase_client.client.table('messages').select('count', count='exact').limit(1).execute()
                        status_checks.append(("Supabase Database", True, "Connected (client.table method)"))
                    except Exception as e1:
                        try:
                            result = supabase_client.table('messages').select('count', count='exact').limit(1).execute()
                            status_checks.append(("Supabase Database", True, "Connected (table method)"))
                        except Exception as e2:
                            try:
                                result = supabase_client.client.from_('messages').select('count', count='exact').limit(1).execute()
                                status_checks.append(("Supabase Database", True, "Connected (from_ method)"))
                            except Exception as e3:
                                status_checks.append(("Supabase Database", False, "All connection methods failed"))
                except Exception as e:
                    status_checks.append(("Supabase Database", False, str(e)))
        except Exception as e:
            status_checks.append(("Supabase Database", False, str(e)))
            
        # Check Message Processor
        try:
            message_processor = components.get('message_processor')
            if not message_processor:
                status_checks.append(("Message Processor", False, "Component not initialized"))
            else:
                status_checks.append(("Message Processor", True, f"Initialized (Target language: {message_processor.target_language})"))
        except Exception as e:
            status_checks.append(("Message Processor", False, str(e)))
            
        # Check Config Manager
        try:
            config_manager = components.get('config_manager')
            if not config_manager:
                status_checks.append(("Configuration Manager", False, "Component not initialized"))
            else:
                status_checks.append(("Configuration Manager", True, "Initialized"))
        except Exception as e:
            status_checks.append(("Configuration Manager", False, str(e)))
            
        # Display results
        max_service_name_length = max(len(service) for service, _, _ in status_checks)
        
        for service, status, message in status_checks:
            status_icon = "✅" if status else "❌"
            service_name_padded = service.ljust(max_service_name_length + 2)
            print(f"{status_icon} {service_name_padded} - {message}")
            
        print("-" * 50)
        
        # Overall status
        success_count = sum(1 for _, status, _ in status_checks if status)
        print(f"\nOverall status: {success_count}/{len(status_checks)} services online")
        
        if success_count == len(status_checks):
            print("\n✨ All services are operational! ✨")
        elif success_count > 0:
            print("\n⚠️ Some services are experiencing issues")
        else:
            print("\n🚨 All services are offline or experiencing issues")
            
    except Exception as e:
        logger.error(f"Error checking services status: {str(e)}", exc_info=True)
        print(f"\n❌ Error checking services: {str(e)}")

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

def deep_inspect_whatsapp_client(components):
    """
    Perform a deep inspection of the WhatsApp API client
    to diagnose any issues with the client structure.
    
    Args:
        components (dict): Dictionary of initialized components
    """
    try:
        print("\n🔍 Deep Inspection of WhatsApp API Client\n")
        print("=" * 50)
        
        # Get the Green API client
        green_api = components.get('green_api_client')
        
        if not green_api:
            print("❌ WhatsApp API Client not found in components")
            return
            
        # Basic information
        print(f"Client Object Type: {type(green_api)}")
        print(f"Client Object ID: {id(green_api)}")
        print(f"Client String Representation: {str(green_api)}")
        print("-" * 50)
        
        # Check if it's callable
        print(f"Is Callable: {callable(green_api)}")
        
        # Check if it has __dict__
        has_dict = hasattr(green_api, '__dict__')
        print(f"Has __dict__: {has_dict}")
        
        # If it has __dict__, show its contents
        if has_dict and green_api.__dict__:
            print("\nAttributes in __dict__:")
            for attr_name, attr_value in green_api.__dict__.items():
                # Safely represent the value
                if isinstance(attr_value, str) and len(attr_value) > 50:
                    value_repr = f"{attr_value[:47]}..."
                else:
                    try:
                        value_repr = repr(attr_value)
                        if len(value_repr) > 50:
                            value_repr = f"{value_repr[:47]}..."
                    except:
                        value_repr = "[Complex Object]"
                        
                print(f"- {attr_name}: {value_repr}")
        
        # Check for common attributes that might exist in the client
        print("\nChecking Common Attributes:")
        common_attrs = [
            'id_instance', 'api_token_instance', 'host', 'api_key', 'token', 
            'base_url', 'instance_id', 'url', 'send_message', 'get_groups'
        ]
        
        for attr in common_attrs:
            if hasattr(green_api, attr):
                attr_value = getattr(green_api, attr)
                print(f"✅ Has '{attr}': {repr(attr_value)[:50] if len(repr(attr_value)) > 50 else repr(attr_value)}")
            else:
                print(f"❌ No '{attr}' attribute")
        
        # Inspect all public attributes and methods
        print("\nAll Public Attributes and Methods:")
        
        # Get all attributes that don't start with underscore
        all_attrs = [a for a in dir(green_api) if not a.startswith('_')]
        
        for attr in all_attrs:
            try:
                # Get the attribute/method
                attr_value = getattr(green_api, attr)
                
                # Check if it's a method
                is_method = callable(attr_value)
                
                # Represent the attribute/method appropriately
                if is_method:
                    print(f"- Method: {attr}()")
                else:
                    # For attributes, show their values safely
                    if isinstance(attr_value, str) and len(attr_value) > 50:
                        value_repr = f"{attr_value[:47]}..."
                    else:
                        try:
                            value_repr = repr(attr_value)
                            if len(value_repr) > 50:
                                value_repr = f"{value_repr[:47]}..."
                        except:
                            value_repr = "[Complex Object]"
                            
                    print(f"- Attribute: {attr} = {value_repr}")
            except Exception as e:
                print(f"- Error accessing {attr}: {str(e)}")
        
        # Try to call a common method if available
        print("\nTrying to Access Common Methods:")
        
        common_methods = [
            ('send_message', {'chat_id': 'test', 'message': 'test'}),
            ('get_settings', {}),
            ('get_state_instance', {}),
            ('get_status_instance', {}),
            ('get_contacts', {})
        ]
        
        for method_name, args in common_methods:
            if hasattr(green_api, method_name) and callable(getattr(green_api, method_name)):
                print(f"Found method: {method_name}()")
                
                # Don't actually call the methods to avoid side effects
                print(f"  (Not calling to avoid side effects)")
            else:
                print(f"Method not found: {method_name}()")
        
        # Suggest a fix based on findings
        print("\n📋 Diagnostic Summary:")
        print("-" * 50)
        
        if not has_dict or not green_api.__dict__:
            print("The client doesn't have a standard __dict__ attribute structure.")
            print("This means it's likely a proxy object or a custom implementation.")
            
        print("\nBased on the inspection, consider updating the check_services_status function to:")
        print("1. Look for particular methods rather than attributes")
        print("2. Check for any of the detected attributes or methods")
        print("3. Update the service status check to match the actual structure")
        
        print("\n💡 Suggestion for fixing service status check:")
        print("Modify the check_services_status function to look for the attributes/methods")
        print("that were found during this inspection.")
            
    except Exception as e:
        logger.error(f"Error inspecting WhatsApp API client: {str(e)}", exc_info=True)
        print(f"\n❌ Error inspecting client: {str(e)}")

if __name__ == "__main__":
    # Test environment variables function
    view_environment_variables() 