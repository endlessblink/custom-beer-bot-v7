#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Green API Client Module

This module implements a client for the WhatsApp Green API service.
It provides methods for sending and receiving messages, checking status,
and managing WhatsApp connections.
"""

import json
import logging
import time
import os
from typing import Any, Dict, List, Optional, Union
import requests
from tenacity import retry, stop_after_attempt, wait_exponential


class GreenAPIClient:
    """
    Green API Client for WhatsApp
    
    This class provides methods for interacting with the WhatsApp Green API.
    """
    
    def __init__(self, 
                 instance_id: str, 
                 instance_token: str, 
                 base_url: str = "https://api.greenapi.com",
                 api_delay: int = 1000):
        """
        Initialize the Green API client
        
        Args:
            instance_id (str): Green API instance ID
            instance_token (str): Green API API token
            base_url (str, optional): Base URL for API. Defaults to "https://api.greenapi.com".
            api_delay (int, optional): Delay between API calls in milliseconds. Defaults to 1000.
        """
        self.instance_id = instance_id
        self.instance_token = instance_token
        self.base_url = base_url
        # Convert api_delay to int first, then divide
        self.api_delay = int(api_delay) / 1000  # Convert to seconds
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"Green API client initialized for instance {instance_id}")
    
    def _build_url(self, endpoint: str) -> str:
        """
        Build a URL for an API endpoint
        
        Args:
            endpoint (str): API endpoint
            
        Returns:
            str: Full API URL
        """
        return f"{self.base_url}/waInstance{self.instance_id}/{endpoint}/{self.instance_token}"
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def _make_request(self, 
                      method: str, 
                      endpoint: str, 
                      payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make an API request with retries
        
        Args:
            method (str): HTTP method (GET, POST, etc.)
            endpoint (str): API endpoint
            payload (Dict[str, Any], optional): Request payload. Defaults to None.
            
        Returns:
            Dict[str, Any]: API response
            
        Raises:
            Exception: If API request fails after retries
        """
        url = self._build_url(endpoint)
        headers = {'Content-Type': 'application/json'}
        
        self.logger.debug(f"Making {method} request to {endpoint}")
        
        try:
            # Add a small delay to avoid rate limiting
            time.sleep(self.api_delay)
            
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(
                    url, 
                    headers=headers, 
                    data=json.dumps(payload) if payload else None,
                    timeout=30
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Raise exception for HTTP errors
            response.raise_for_status()
            
            # Parse JSON response
            if response.text:
                result = response.json()
            else:
                result = {}
            
            return result
        
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {str(e)}")
            raise
    
    def get_instance_status(self) -> Dict[str, Any]:
        """
        Get the status of the WhatsApp instance
        
        Returns:
            Dict[str, Any]: Instance status information
        """
        return self._make_request('GET', 'getStateInstance')
    
    def send_message(self, chat_id: str, message: str, is_summary: bool = False) -> Dict[str, Any]:
        """
        Send a message to a chat or group.
        RESTRICTION: Only summary messages are allowed to be sent.
        
        Args:
            chat_id (str): Chat ID (e.g., "1234567890@c.us" for a personal chat or "1234567890-1234567890@g.us" for a group)
            message (str): Message text
            is_summary (bool): Flag indicating if this message is a summary. Only summary messages are allowed to be sent.
            
        Returns:
            Dict[str, Any]: Response from the API or dummy response if not a summary
        """
        # GLOBAL SAFETY MEASURE: Force disable all message sending
        # This is a hard-coded safety measure that overrides all other settings
        force_disable_messages = True
        
        if force_disable_messages:
            self.logger.warning("🛑 SAFETY MEASURE ACTIVE: All message sending is disabled by a hard-coded safety measure.")
            self.logger.info(f"Would have sent message to {chat_id}: {message[:50]}...")
            return {
                "idMessage": "SAFETY-DISABLED-XXXX",
                "status": "disabled",
                "message": "Message sending has been disabled by a safety measure"
            }
        
        # Check if message sending is explicitly disabled
        message_sending_disabled = os.environ.get('BOT_MESSAGE_SENDING_DISABLED', 'false').lower() == 'true'
        
        if message_sending_disabled:
            self.logger.warning("🛑 MESSAGE SENDING DISABLED: The bot attempted to send a message but sending is disabled in configuration.")
            self.logger.info(f"Would have sent message to {chat_id}: {message[:50]}...")
            return {
                "idMessage": "DISABLED-MESSAGE-SENDING-XXXX",
                "status": "disabled",
                "message": "Message sending has been disabled in configuration"
            }
            
        # Only allow summary messages
        if not is_summary:
            self.logger.warning("🛑 NON-SUMMARY MESSAGE BLOCKED: The bot attempted to send a non-summary message.")
            self.logger.info(f"Blocked non-summary message to {chat_id}: {message[:50]}...")
            return {
                "idMessage": "NON-SUMMARY-BLOCKED-XXXX",
                "status": "blocked",
                "message": "Only summary messages are allowed to be sent"
            }
        
        # This point is reached only for summary messages when sending is not disabled
        self.logger.info(f"Sending summary message to {chat_id}")
        
        # Send the actual message
        response = self._make_request('POST', 'sendMessage', {
            'chatId': chat_id,
            'message': message
        })
        
        return response
    
    def get_chat_history(self, 
                        chat_id: str, 
                        count: int = 100) -> List[Dict[str, Any]]:
        """
        Get chat history
        
        Args:
            chat_id (str): Chat ID
            count (int, optional): Number of messages to retrieve. Defaults to 100.
            
        Returns:
            List[Dict[str, Any]]: List of messages
        """
        payload = {
            'chatId': chat_id,
            'count': count
        }
        
        self.logger.info(f"Getting chat history for {chat_id}")
        return self._make_request('POST', 'getChatHistory', payload)
    
    def get_contacts(self) -> List[Dict[str, Any]]:
        """
        Get contacts list
        
        Returns:
            List[Dict[str, Any]]: List of contacts
        """
        self.logger.info("Getting contacts list")
        return self._make_request('GET', 'getContacts')
    
    def receive_notification(self) -> Optional[Dict[str, Any]]:
        """
        Receive a notification
        
        Returns:
            Dict[str, Any]: Notification data or None if no notification
        """
        try:
            return self._make_request('GET', 'receiveNotification')
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # No notifications, not an error
                return None
            raise
    
    def delete_notification(self, receipt_id: str) -> Dict[str, Any]:
        """
        Delete a notification after processing
        
        Args:
            receipt_id (str): Notification receipt ID
            
        Returns:
            Dict[str, Any]: API response
        """
        return self._make_request('DELETE', f'deleteNotification/{receipt_id}')
    
    def mark_as_read(self, chat_id: str, message_id: str) -> Dict[str, Any]:
        """
        Mark a message as read
        
        Args:
            chat_id (str): Chat ID
            message_id (str): Message ID
            
        Returns:
            Dict[str, Any]: API response
        """
        payload = {
            'chatId': chat_id,
            'idMessage': message_id
        }
        
        return self._make_request('POST', 'readChat', payload)
    
    def get_available_webhooks(self) -> Dict[str, Any]:
        """
        Get information about available webhooks
        
        Returns:
            Dict[str, Any]: Webhook information
        """
        return self._make_request('GET', 'getAvailableWebhooks')
    
    def set_webhook_url(self, webhook_url: str) -> Dict[str, Any]:
        """
        Set a webhook URL
        
        Args:
            webhook_url (str): Webhook URL
            
        Returns:
            Dict[str, Any]: API response
        """
        payload = {
            'webhookUrl': webhook_url
        }
        
        return self._make_request('POST', 'setWebhookUrl', payload) 