#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Group Manager Module

This module provides functionality for managing WhatsApp groups through Green API.
It handles group listing, selection, and data retrieval.
"""

import logging
from typing import Any, Dict, List, Optional

from green_api.client import GreenAPIClient


class GroupManager:
    """
    Group Manager for WhatsApp Groups
    
    This class provides methods for working with WhatsApp groups.
    """
    
    def __init__(self, green_api_client: GreenAPIClient):
        """
        Initialize the group manager
        
        Args:
            green_api_client (GreenAPIClient): Green API client instance
        """
        self.client = green_api_client
        self.logger = logging.getLogger(__name__)
        self.logger.info("Group manager initialized")
    
    def get_groups(self) -> List[Dict[str, Any]]:
        """
        Get a list of available WhatsApp groups
        
        Returns:
            List[Dict[str, Any]]: List of group information
        """
        self.logger.info("Fetching available groups")
        
        # Get all chats
        contacts = self.client.get_contacts()
        
        # Filter for groups (group IDs end with @g.us)
        groups = [
            {
                'id': contact['id'],
                'name': contact.get('name', 'Unknown Group'),
                'type': 'group'
            }
            for contact in contacts
            if contact['id'].endswith('@g.us')
        ]
        
        self.logger.info(f"Found {len(groups)} groups")
        return groups
    
    def get_group_data(self, group_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific group
        
        Args:
            group_id (str): Group ID
            
        Returns:
            Dict[str, Any]: Group data
            
        Raises:
            Exception: If group data cannot be retrieved
        """
        self.logger.info(f"Fetching data for group {group_id}")
        
        # Validate group ID format
        if not group_id.endswith('@g.us'):
            self.logger.error(f"Invalid group ID format: {group_id}")
            raise ValueError("Group ID must end with @g.us")
        
        # Get group data
        try:
            group_data = self.client._make_request('POST', 'getGroupData', {'groupId': group_id})
            self.logger.debug(f"Group data retrieved: {group_data}")
            return group_data
        except Exception as e:
            self.logger.error(f"Failed to get group data: {str(e)}")
            raise
    
    def validate_group_access(self, group_id: str) -> bool:
        """
        Validate that the bot has access to the specified group
        
        Args:
            group_id (str): Group ID
            
        Returns:
            bool: True if the bot has access, False otherwise
        """
        try:
            group_data = self.get_group_data(group_id)
            # Check if we're a participant
            instance_number = self.client._make_request('GET', 'getSettings')['wid']
            
            for participant in group_data.get('participants', []):
                if participant['id'] == instance_number:
                    self.logger.info(f"Bot is a participant in group {group_id}")
                    return True
            
            self.logger.warning(f"Bot is not a participant in group {group_id}")
            return False
        except Exception as e:
            self.logger.error(f"Error validating group access: {str(e)}")
            return False
    
    def get_group_participants(self, group_id: str) -> List[Dict[str, Any]]:
        """
        Get a list of participants in a group
        
        Args:
            group_id (str): Group ID
            
        Returns:
            List[Dict[str, Any]]: List of participant information
        """
        try:
            group_data = self.get_group_data(group_id)
            return group_data.get('participants', [])
        except Exception as e:
            self.logger.error(f"Error getting group participants: {str(e)}")
            return []
    
    def get_group_name(self, group_id: str) -> str:
        """
        Get the name of a group
        
        Args:
            group_id (str): Group ID
            
        Returns:
            str: Group name or "Unknown Group" if not found
        """
        try:
            group_data = self.get_group_data(group_id)
            return group_data.get('subject', 'Unknown Group')
        except Exception:
            return "Unknown Group" 