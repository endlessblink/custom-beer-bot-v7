#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Group Selection Module

This module handles WhatsApp group selection for the menu interface.
"""

import logging
from utils.menu.core_menu import show_menu, display_error_and_continue

logger = logging.getLogger("whatsapp_bot")

def select_group(components):
    """
    Allow user to select a WhatsApp group
    
    Args:
        components (dict): Dictionary of components including group_manager
    
    Returns:
        dict: Selected group data with id and name, or None if failed
    """
    try:
        # Get group manager
        group_manager = components.get('group_manager')
        if not group_manager:
            logger.error("Group manager not found in components")
            display_error_and_continue("Failed to initialize group manager")
            return None
        
        # Get groups
        logger.info("Fetching WhatsApp groups...")
        groups = group_manager.get_groups()
        
        if not groups or not isinstance(groups, list) or len(groups) == 0:
            logger.warning("No WhatsApp groups found")
            display_error_and_continue("No WhatsApp groups found. Please ensure you have joined at least one group.")
            return None
        
        logger.info(f"Found {len(groups)} WhatsApp groups")
        
        # Display selection menu
        print(f"\nFound {len(groups)} WhatsApp groups:")
        
        options = []
        for idx, group in enumerate(groups):
            group_id = group.get('id', 'Unknown ID')
            group_name = group.get('name', group_id)
            options.append({
                'key': str(idx + 1),
                'text': f"{group_name} ({group_id})"
            })
        
        options.append({'key': 'c', 'text': 'Cancel'})
        
        choice = show_menu("Select a group", options)
        
        if choice.lower() == 'c':
            logger.info("User canceled group selection")
            return None
        
        try:
            group_idx = int(choice) - 1
            if group_idx < 0 or group_idx >= len(groups):
                logger.warning(f"Invalid group selection: {choice}")
                display_error_and_continue("Invalid group selection")
                return None
                
            selected_group = groups[group_idx]
            logger.info(f"Group selected: {selected_group.get('name', selected_group.get('id', 'Unknown'))}")
            return selected_group
            
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse group selection: {str(e)}")
            display_error_and_continue("Invalid selection format")
            return None
        
    except Exception as e:
        logger.error(f"Error selecting group: {str(e)}", exc_info=True)
        display_error_and_continue(f"Error selecting group: {str(e)}")
        return None 