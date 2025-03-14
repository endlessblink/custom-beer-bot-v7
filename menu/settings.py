#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Settings Menu Module

This module provides a way to view and modify application settings.
"""

import os
import json
import logging
from utils.menu.core_menu import show_menu, display_error_and_continue

logger = logging.getLogger("whatsapp_bot")

# Path for user settings
USER_SETTINGS_PATH = "user_settings.json"

def load_user_settings():
    """
    Load user settings from the settings file
    
    These settings will override environment variables with the same name.
    """
    try:
        if not os.path.exists(USER_SETTINGS_PATH):
            logger.info("No user settings file found, creating default")
            create_default_settings()
            
        with open(USER_SETTINGS_PATH, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            
        # Set environment variables from settings
        for key, value in settings.items():
            logger.debug(f"Setting environment variable from user settings: {key}")
            os.environ[key] = str(value)
            
        logger.info(f"Loaded {len(settings)} user settings")
        return settings
        
    except Exception as e:
        logger.error(f"Error loading user settings: {str(e)}", exc_info=True)
        return {}

def save_user_settings(settings):
    """
    Save user settings to the settings file
    
    Args:
        settings (dict): Settings to save
        
    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(USER_SETTINGS_PATH), exist_ok=True)
        
        with open(USER_SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4)
            
        logger.info(f"Saved {len(settings)} user settings")
        return True
        
    except Exception as e:
        logger.error(f"Error saving user settings: {str(e)}", exc_info=True)
        return False

def create_default_settings():
    """
    Create default user settings file
    
    Returns:
        bool: True if created successfully, False otherwise
    """
    default_settings = {
        "SEND_MESSAGES_DISABLED": "True"
    }
    
    return save_user_settings(default_settings)

def get_current_settings():
    """
    Get current user settings
    
    Returns:
        dict: Current settings
    """
    try:
        if not os.path.exists(USER_SETTINGS_PATH):
            return create_default_settings()
            
        with open(USER_SETTINGS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    except Exception as e:
        logger.error(f"Error reading settings: {str(e)}", exc_info=True)
        return {}

def settings_menu(components):
    """
    Display and manage user settings
    
    Args:
        components (dict): Dictionary of components
    """
    while True:
        try:
            settings = get_current_settings()
            
            print("\nCurrent Settings:")
            for key, value in settings.items():
                print(f"{key}: {value}")
                
            options = [
                {'key': '1', 'text': 'Toggle Message Sending Safety'},
                {'key': '2', 'text': 'Back to Main Menu'}
            ]
            
            choice = show_menu("Settings Menu", options)
            
            if choice == '1':
                # Toggle message sending safety
                current = settings.get('SEND_MESSAGES_DISABLED', 'True')
                new_value = 'False' if current.lower() == 'true' else 'True'
                
                settings['SEND_MESSAGES_DISABLED'] = new_value
                
                if save_user_settings(settings):
                    # Update environment variable
                    os.environ['SEND_MESSAGES_DISABLED'] = new_value
                    
                    state = "DISABLED" if new_value.lower() == 'true' else "ENABLED"
                    print(f"\n✅ Message sending is now {state}")
                    logger.info(f"Message sending safety set to: {new_value}")
                else:
                    print("\n❌ Failed to save settings")
                    
                input("\nPress Enter to continue...")
                
            elif choice == '2':
                # Return to main menu
                return
                
        except Exception as e:
            logger.error(f"Error in settings menu: {str(e)}", exc_info=True)
            display_error_and_continue(f"Error: {str(e)}")
            
if __name__ == "__main__":
    # Test settings functionality
    print("Current settings:", get_current_settings())
    create_default_settings()
    print("Default settings created") 