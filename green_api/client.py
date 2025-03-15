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
                        count: int = 300,
                        min_count: int = 100) -> List[Dict[str, Any]]:
        """
        Get chat history
        
        Args:
            chat_id (str): Chat ID
            count (int, optional): Number of messages to retrieve. Defaults to 300.
            min_count (int, optional): Minimum number of messages to retrieve. If fewer messages
                                      are returned, multiple requests will be made. Defaults to 100.
            
        Returns:
            List[Dict[str, Any]]: List of messages
        """
        payload = {
            'chatId': chat_id,
            'count': count
        }
        
        self.logger.info(f"Getting chat history for {chat_id} (requesting {count} messages, minimum {min_count})")
        
        # Try a larger initial request if min_count is significant
        if min_count > 500:
            payload['count'] = max(count, min_count * 2)  # Make sure we request at least 2x the minimum
            self.logger.info(f"Increased initial request to {payload['count']} messages due to high minimum requirement")
        
        try:
            messages = self._make_request('POST', 'getChatHistory', payload)
            self.logger.info(f"Initial request returned {len(messages)} messages")
            
            # Add some diagnostic logging to understand the response structure
            if messages and len(messages) > 0:
                self.logger.debug(f"First message sample - keys: {list(messages[0].keys())}")
                self.logger.debug(f"First message sample - timesstamp value: {messages[0].get('timestamp')}")
                self.logger.debug(f"First message sample - timestamp type: {type(messages[0].get('timestamp'))}")
                self.logger.debug(f"First message sample - ID: {messages[0].get('idMessage')}")
            
            # Check if we have enough messages
            if min_count > 0 and len(messages) < min_count:
                self.logger.info(f"Retrieved only {len(messages)} messages, which is less than the minimum {min_count}. Attempting to fetch more.")
                
                # If we have very few messages, it might mean the chat is new or has little history
                if len(messages) < 10:
                    self.logger.warning(f"Very few messages ({len(messages)}) found. This might be a new chat or one with little history.")
                    
                    # In this case, we'll try to get all available history by using different parameters
                    try:
                        # Try fetching with an alternative method (if available)
                        alt_payload = {
                            'chatId': chat_id,
                            'count': max(500, min_count * 3)  # Try a much larger count
                        }
                        self.logger.info(f"Trying alternative fetch with count={alt_payload['count']}")
                        
                        alt_messages = self._make_request('POST', 'getChatHistory', alt_payload)
                        if alt_messages and len(alt_messages) > len(messages):
                            self.logger.info(f"Alternative fetch successful! Got {len(alt_messages)} messages")
                            messages = alt_messages
                    except Exception as e:
                        self.logger.warning(f"Alternative fetch method failed: {str(e)}")
                
                # Make additional requests if needed to reach minimum count
                # We'll make up to 5 additional attempts to get more messages (increased from 3)
                attempts = 0
                max_attempts = 5
                total_messages = len(messages)
                
                while total_messages < min_count and attempts < max_attempts:
                    attempts += 1
                    
                    # Get the ID of the last message to use as a starting point
                    if messages and len(messages) > 0:
                        try:
                            last_message = messages[-1]  # Get the last message
                            self.logger.debug(f"Last message for pagination - keys: {list(last_message.keys())}")
                            
                            last_message_id = last_message.get('idMessage')
                            if last_message_id:
                                # Add the lastMessageId parameter to get older messages
                                payload['lastMessageId'] = last_message_id
                                
                                # Increase the count to fetch more messages each time
                                payload['count'] = count * (attempts + 1)
                                
                                # Request more messages
                                self.logger.info(f"Fetching additional messages (attempt {attempts}/{max_attempts}, requesting {payload['count']} messages, starting from ID {last_message_id})")
                                additional_messages = self._make_request('POST', 'getChatHistory', payload)
                                
                                if additional_messages:
                                    # Check if we're getting new messages or duplicates
                                    existing_ids = {msg.get('idMessage') for msg in messages if 'idMessage' in msg}
                                    new_messages = [msg for msg in additional_messages if msg.get('idMessage') not in existing_ids]
                                    
                                    if new_messages:
                                        # Add only the new messages to our list
                                        messages.extend(new_messages)
                                        total_messages = len(messages)
                                        self.logger.info(f"Retrieved {len(new_messages)} new messages out of {len(additional_messages)} additional messages, total now: {total_messages}")
                                    else:
                                        self.logger.warning(f"No new messages found in the additional {len(additional_messages)} messages, stopping pagination")
                                        break
                                else:
                                    self.logger.warning("No additional messages returned, stopping pagination")
                                    break
                            else:
                                self.logger.warning("Could not find ID of last message, stopping pagination")
                                break
                        except Exception as e:
                            self.logger.error(f"Error during pagination: {str(e)}")
                            break
                    else:
                        # No messages at all, nothing more to fetch
                        break
                
                if total_messages < min_count:
                    self.logger.warning(f"Could only retrieve {total_messages} messages, which is less than the requested minimum {min_count}")
            
            # Log a sample of the messages for debugging
            if messages and len(messages) > 0:
                self.logger.debug(f"Final message sample - first message type: {messages[0].get('typeMessage')}")
                if 'timestamp' in messages[0]:
                    self.logger.debug(f"Final message sample - first message timestamp: {messages[0].get('timestamp')}")
                
                # Count message types
                message_types = {}
                for msg in messages:
                    msg_type = msg.get('typeMessage', 'unknown')
                    message_types[msg_type] = message_types.get(msg_type, 0) + 1
                self.logger.info(f"Message types in the result: {message_types}")
            
            # Ensure all timestamps are standardized to integers if possible
            for msg in messages:
                if 'timestamp' in msg and msg['timestamp'] is not None:
                    if isinstance(msg['timestamp'], str):
                        try:
                            msg['timestamp'] = int(msg['timestamp'])
                        except (ValueError, TypeError):
                            # Leave it as a string if conversion fails
                            pass
            
            return messages
            
        except Exception as e:
            self.logger.error(f"Error getting chat history: {str(e)}")
            return []
    
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