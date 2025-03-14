#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Core Menu Functionality

This module contains the core menu initialization and main menu loop.
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
from utils.menu.core_menu import (
    clear_screen,
    print_header,
    show_menu,
    display_error_and_continue,
    confirm_action
)

# Setup logging
logger = setup_logger("INFO")

# Constants
MAX_FATAL_ERROR_RETRIES = 3

def initialize_components(fatal_error_retries=0):
    """
    Initialize all necessary components
    
    Args:
        fatal_error_retries: Number of retries already attempted for fatal errors
        
    Returns:
        dict: Dictionary of initialized components
        
    Raises:
        ValueError: If required configuration is missing
        ConnectionError: If unable to connect to external services
    """
    try:
        logger.info("Starting component initialization")
        
        # Load environment variables
        load_dotenv(override=True)
        logger.info("Environment variables loaded")
        
        # Load user settings (overrides env vars)
        from menu.settings import load_user_settings
        load_user_settings()
        logger.info("User settings loaded")
        
        # Create config manager
        config_manager = ConfigManager()
        
        # Validate required configuration
        required_configs = [
            'GREEN_API_ID_INSTANCE',
            'GREEN_API_TOKEN',
            'GREEN_API_BASE_URL',
            'OPENAI_API_KEY',
            'SUPABASE_URL',
            'SUPABASE_KEY'
        ]
        
        missing_configs = [config for config in required_configs 
                         if not config_manager.get(config)]
        
        if missing_configs:
            error_msg = f"Missing required configuration: {', '.join(missing_configs)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Initialize components with validation
        components = {}
        
        try:
            # Initialize Green API client
            logger.info("Initializing Green API client...")
            green_api_client = GreenAPIClient(
                instance_id=config_manager.get('GREEN_API_ID_INSTANCE'),
                instance_token=config_manager.get('GREEN_API_TOKEN'),
                base_url=config_manager.get('GREEN_API_BASE_URL')
            )
            components['green_api_client'] = green_api_client
            
            # Initialize Group Manager
            logger.info("Initializing Group Manager...")
            group_manager = GroupManager(green_api_client)
            components['group_manager'] = group_manager
            
            # Initialize OpenAI client
            logger.info("Initializing OpenAI client...")
            openai_client = OpenAIClient(
                api_key=config_manager.get('OPENAI_API_KEY'),
                model=config_manager.get('OPENAI_MODEL', 'gpt-4-turbo-preview'),
                max_tokens=int(config_manager.get('OPENAI_MAX_TOKENS', 2000))
            )
            components['openai_client'] = openai_client
            
            # Initialize message processor
            logger.info("Initializing Message Processor...")
            message_processor = MessageProcessor(
                target_language=config_manager.get('BOT_TARGET_LANGUAGE', 'hebrew')
            )
            components['message_processor'] = message_processor
            
            # Initialize Supabase client with simple validation
            logger.info("Initializing Supabase client...")
            try:
                supabase_client = SupabaseClient(
                    url=config_manager.get('SUPABASE_URL'),
                    key=config_manager.get('SUPABASE_KEY')
                )
                
                # Simple validation - only check if client property exists
                if hasattr(supabase_client, 'client') and supabase_client.client:
                    logger.info("Supabase client initialized successfully")
                    components['supabase_client'] = supabase_client
                else:
                    logger.error("Supabase client not properly initialized")
                    raise ConnectionError("Supabase client not properly initialized")
                    
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {str(e)}", exc_info=True)
                if fatal_error_retries < MAX_FATAL_ERROR_RETRIES:
                    logger.info(f"Retrying initialization (attempt {fatal_error_retries + 1}/{MAX_FATAL_ERROR_RETRIES})")
                    time.sleep(2)  # Wait before retrying
                    return initialize_components(fatal_error_retries + 1)
                else:
                    logger.error("Max retry attempts reached. Could not initialize Supabase client.")
                    raise ConnectionError(f"Failed to connect to Supabase after {MAX_FATAL_ERROR_RETRIES} attempts: {str(e)}")
            
            components['config_manager'] = config_manager
            
            # Validate all components are initialized
            required_components = [
                'green_api_client',
                'group_manager',
                'openai_client',
                'message_processor',
                'supabase_client',
                'config_manager'
            ]
            
            missing_components = [comp for comp in required_components 
                               if comp not in components]
            
            if missing_components:
                raise ValueError(f"Failed to initialize components: {', '.join(missing_components)}")
            
            logger.info("All components initialized successfully")
            return components
            
        except Exception as e:
            logger.error(f"Component initialization failed: {str(e)}", exc_info=True)
            raise
    
    except Exception as e:
        logger.error(f"Fatal error during initialization: {str(e)}", exc_info=True)
        raise

def run_main_menu():
    """
    Run the main menu loop
    
    This function handles the main application loop and menu interactions.
    It includes error handling and graceful degradation for component failures.
    """
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            components = initialize_components()
            logger.info("Main menu started successfully")
            
            while True:
                try:
                    print_header()
                    
                    options = [
                        {'key': '1', 'text': 'Generate New Summary'},
                        {'key': '2', 'text': 'Settings'},
                        {'key': '3', 'text': 'Debug Menu'},
                        {'key': '4', 'text': 'Exit'}
                    ]
                    
                    choice = show_menu("Main Menu", options)
                    
                    if choice == '1':
                        from menu.groups import select_group
                        from menu.summary import select_days, generate_summary, send_summary
                        
                        try:
                            logger.info("Starting summary generation flow")
                            
                            # Select group with validation
                            print("\nSelecting group...")
                            group = select_group(components)
                            if not group or not isinstance(group, dict) or 'id' not in group:
                                logger.error("Invalid group selection result")
                                print("\n❌ Invalid group selection")
                                input("\nPress Enter to continue...")
                                continue
                            
                            group_name = group.get('name', group.get('id', 'Unknown'))
                            logger.info(f"Group selected: {group_name}")
                            print(f"\nSelected group: {group_name}")
                            
                            # Select time period with validation
                            print("\nSelecting time period...")
                            days = select_days()
                            if not isinstance(days, int) or days <= 0:
                                logger.error(f"Invalid time period selected: {days}")
                                print("\n❌ Invalid time period")
                                input("\nPress Enter to continue...")
                                continue
                            
                            logger.info(f"Time period selected: {days} days")
                            
                            # Ask user whether to use API or database
                            print("\nWhere would you like to get messages from?")
                            data_source_options = [
                                {'key': '1', 'text': 'Fetch fresh messages from WhatsApp (API)'},
                                {'key': '2', 'text': 'Use existing messages from database'}
                            ]
                            data_source = show_menu("Data Source", data_source_options)
                            use_api = (data_source == '1')
                            
                            if use_api:
                                print(f"\nGenerating summary for the last {days} days using fresh WhatsApp messages...")
                            else:
                                print(f"\nGenerating summary for the last {days} days using database messages...")
                            
                            # Generate and validate summary
                            summary = generate_summary(components, group['id'], days, use_api)
                            if not summary or not isinstance(summary, str):
                                logger.error("Invalid summary generated")
                                print("\n❌ Failed to generate valid summary")
                                input("\nPress Enter to continue...")
                                continue
                            
                            if len(summary.strip()) == 0:
                                logger.error("Empty summary generated")
                                print("\n❌ Generated summary is empty")
                                input("\nPress Enter to continue...")
                                continue
                            
                            logger.info(f"Summary generated successfully ({len(summary)} chars)")
                            print("\n✅ Summary generated!")
                            print("\nSending summary to group...")
                            
                            # Send summary with retry
                            max_send_retries = 3
                            send_result = send_summary(components, group['id'], summary)
                            
                            # Handle different send_summary result values
                            if send_result is True:
                                # Success on first try
                                logger.info("Summary sent successfully")
                                print("\n✅ Summary sent successfully!")
                            elif send_result is None:
                                # User explicitly declined to send
                                logger.info("User declined to send summary - not retrying")
                                print("\nSummary not sent per user request")
                            elif send_result is False:
                                # Technical error - retry
                                retry_success = False
                                for attempt in range(max_send_retries - 1):  # -1 because we already tried once
                                    logger.warning(f"Retrying summary send (attempt {attempt + 2}/{max_send_retries})")
                                    time.sleep(2)  # Wait before retry
                                    retry_result = send_summary(components, group['id'], summary)
                                    
                                    # Check each retry result
                                    if retry_result is True:
                                        logger.info("Summary sent successfully on retry")
                                        print("\n✅ Summary sent successfully on retry!")
                                        retry_success = True
                                        break
                                    elif retry_result is None:
                                        # User declined on retry - don't continue retrying
                                        logger.info("User declined to send summary during retry - stopping retries")
                                        print("\nSummary not sent per user request")
                                        retry_success = True  # Mark as handled
                                        break
                                
                                if not retry_success:
                                    logger.error("Failed to send summary after all retries")
                                    print("\n❌ Failed to send summary after multiple attempts")
                            else:
                                # Other unexpected return value - don't retry
                                logger.warning(f"Unexpected return value from send_summary: {send_result}")
                                print("\n❌ Unexpected error when sending summary")
                        
                        except Exception as e:
                            logger.error(f"Error in summary generation flow: {str(e)}", exc_info=True)
                            print(f"\n❌ Error: {str(e)}")
                            print("\nPlease check the logs for more details.")
                        
                        input("\nPress Enter to continue...")
                    
                    elif choice == '2':
                        from menu.settings import settings_menu
                        settings_menu(components)
                    
                    elif choice == '3':
                        from menu.debug import debug_menu
                        debug_menu(components)
                    
                    elif choice == '4':
                        logger.info("User requested exit")
                        print("\nGoodbye! 👋")
                        sys.exit(0)
                        
                except KeyboardInterrupt:
                    logger.info("User interrupted operation")
                    print("\n\nOperation cancelled by user")
                    input("\nPress Enter to return to main menu...")
                    continue
                    
                except Exception as e:
                    logger.error(f"Error in menu operation: {str(e)}", exc_info=True)
                    print(f"\n❌ Error: {str(e)}")
                    print("\nReturning to main menu...")
                    time.sleep(2)
                    continue
            
        except Exception as e:
            retry_count += 1
            logger.error(f"Fatal error (attempt {retry_count}/{max_retries}): {str(e)}", exc_info=True)
            print(f"\n❌ Fatal error: {str(e)}")
            
            if retry_count < max_retries:
                print(f"\nRetrying in 5 seconds... (attempt {retry_count + 1}/{max_retries})")
                time.sleep(5)
            else:
                print("\nMaximum retry attempts reached. Please check your configuration and try again.")
                sys.exit(1)

if __name__ == "__main__":
    run_main_menu() 