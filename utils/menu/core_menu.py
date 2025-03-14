#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Core Menu Functionality

This module contains the essential menu functionality that must always
be preserved in the WhatsApp Group Summary Bot. The interactive menu
is a CRITICAL component and should never be removed or broken.

DO NOT MODIFY THIS FILE WITHOUT CAREFUL CONSIDERATION.
"""

import os
import sys
import time
from typing import Dict, Any, List, Optional, Callable


def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title: str = "WHATSAPP GROUP SUMMARY GENERATOR"):
    """Print the application header"""
    clear_screen()
    print("=" * 60)
    print(" " * (30 - len(title) // 2) + title)
    print("=" * 60)
    print()


def show_menu(
    title: str,
    options: List[Dict[str, Any]],
    components: Optional[Dict[str, Any]] = None,
    header_title: str = "WHATSAPP GROUP SUMMARY GENERATOR"
) -> str:
    """
    Display a menu and get user choice.
    
    This is a CORE function that ensures the menu is always displayed
    regardless of the state of other components.
    
    Args:
        title: Menu title
        options: List of menu options. Each option should be a dict with:
                - 'key': The key to press (e.g., '1', '2', 'q')
                - 'text': The text to display
                - 'requires': (optional) List of component keys required for this option
        components: Dictionary of available components (optional)
        header_title: Title to display in the header
    
    Returns:
        The key of the selected option
    """
    while True:
        print_header(header_title)
        print(f"{title}:")
        
        # Always display all options
        for option in options:
            key = option.get('key', '')
            text = option.get('text', '')
            
            # Check if option requires certain components
            required_components = option.get('requires', [])
            is_available = True
            
            if components is not None and required_components:
                for required in required_components:
                    if required not in components or not components[required]:
                        is_available = False
                        break
            
            # Display the option, but mark as unavailable if needed
            unavailable_marker = " (⚠️ Unavailable)" if not is_available else ""
            print(f"{key}. {text}{unavailable_marker}")
        
        choice = input("\nEnter your choice: ").strip()
        
        # Validate the choice
        valid_keys = [option.get('key', '') for option in options]
        if choice in valid_keys:
            selected_option = next((option for option in options if option.get('key') == choice), None)
            
            # If option requires components, check if they're available
            if selected_option:
                required_components = selected_option.get('requires', [])
                if components is not None and required_components:
                    missing_components = []
                    for required in required_components:
                        if required not in components or not components[required]:
                            missing_components.append(required)
                    
                    if missing_components:
                        print(f"\n❌ This option requires: {', '.join(missing_components)}")
                        print("These components are not available. Please check your configuration.")
                        input("\nPress Enter to continue...")
                        continue
            
            return choice
        
        print("\n❌ Invalid choice. Please try again.")
        time.sleep(1)


def display_error_and_continue(message: str):
    """Display an error message and wait for user to press Enter"""
    print(f"\n❌ {message}")
    input("\nPress Enter to continue...")


def confirm_action(prompt: str) -> bool:
    """
    Ask for user confirmation
    
    Args:
        prompt: The prompt to display
        
    Returns:
        True if user confirms, False otherwise
    """
    choice = input(f"\n{prompt} (y/n): ").strip().lower()
    return choice in ['y', 'yes', 'כ', 'כן']


# Ensure these essential menu functions are always importable
__all__ = [
    'clear_screen', 
    'print_header', 
    'show_menu', 
    'display_error_and_continue',
    'confirm_action'
] 