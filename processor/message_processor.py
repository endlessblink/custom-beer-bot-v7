#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Message Processor Module

This module provides functionality for processing WhatsApp messages,
extracting relevant content, and preparing them for summarization.
"""

import logging
import re
import emoji
from datetime import datetime
from typing import Any, Dict, List, Optional
import time


class MessageProcessor:
    """
    Message Processor for WhatsApp messages
    
    This class provides methods for processing WhatsApp messages,
    filtering out irrelevant content, and extracting information.
    """
    
    def __init__(self, target_language='hebrew'):
        """
        Initialize the message processor
        
        Args:
            target_language (str, optional): Target language for processing. Defaults to 'hebrew'.
        """
        self.target_language = target_language
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Message processor initialized with target language: {target_language}")
        self._debug_mode = False  # Add debug mode flag
        
        # Commands to filter out (messages starting with these will be ignored)
        self.command_prefixes = ['!', '/', '.']
        
        # Message types to process
        self.supported_message_types = [
            'textMessage',
            'extendedTextMessage',
            'imageMessage',
            'videoMessage',
            'documentMessage',
            'audioMessage',
            'locationMessage',
            'contactMessage',
            'stickerMessage',
            'reactionMessage',
            'pollMessageData',
            'buttonResponseMessage',
            'listResponseMessage',
            'templateButtonReplyMessage',
            # Add the new message types from the API
            'incoming',
            'outgoing'
        ]
        
        # Reduced filtering - set to True to be more permissive with messages
        # This allows for including more messages in the summary
        self.reduced_filtering = True
        self.logger.info("Initialized with reduced filtering: messages with minimal content will be included")
    
    def set_debug_mode(self, enabled=True):
        """
        Enable or disable debug mode
        
        In debug mode, less filtering is applied to messages to help with
        troubleshooting issues with message processing.
        
        Args:
            enabled (bool, optional): Whether to enable debug mode. Defaults to True.
        """
        self._debug_mode = enabled
        self.logger.info(f"Debug mode {'enabled' if enabled else 'disabled'}")
        return self._debug_mode
    
    def get_debug_mode(self):
        """
        Check if debug mode is enabled
        
        Returns:
            bool: Whether debug mode is enabled
        """
        return self._debug_mode
    
    def process_messages(self, messages):
        """
        Process a list of WhatsApp messages
        
        Args:
            messages (list): List of WhatsApp message objects
            
        Returns:
            list: List of processed message objects
        """
        if not messages:
            self.logger.warning("No messages to process")
            return []
            
        self.logger.info(f"Processing {len(messages)} messages")
        
        # Initialize counters for stats
        processed = 0
        rejected = 0
        
        # Initialize result list
        processed_messages = []
        
        # Define command prefixes to filter out
        command_prefixes = [
            '!', '/', '.', '#',  # Common command prefixes
            '/summary', '!summary', '.summary', '#summary',  # Summary commands
            '/poll', '!poll', '.poll', '#poll',  # Poll commands
            '/help', '!help', '.help', '#help',  # Help commands
        ]
        
        # Check debug mode for logging
        if self._debug_mode:
            self.logger.info("Processing messages in debug mode - less strict filtering will be applied")
        
        # Process each message
        for message in messages:
            try:
                processed += 1
                
                # Basic validation - make sure we have the minimum required fields
                if ('typeMessage' not in message or 
                    ('chatId' not in message and 'chatId' not in message and 'chat_id' not in message)):
                    rejected += 1
                    continue
                
                # In debug mode, we'll keep system messages and others normally filtered
                if not self._debug_mode:
                    # Filter out system messages
                    if message.get('typeMessage') == 'service':
                        rejected += 1
                        continue
                    
                    # Filter out poll messages 
                    if message.get('typeMessage') == 'poll':
                        rejected += 1
                        continue
                        
                    # Filter out certain message types that aren't useful for summaries
                    if (message.get('typeMessage') in ['reaction', 'sticker'] and 
                        not self._debug_mode):  # In debug mode, keep these message types
                        rejected += 1
                        continue
                    
                    # Filter out command messages (if in normal mode)
                    if message.get('typeMessage') == 'textMessage':
                        text = message.get('textMessage', '')
                        if text and text[0] in command_prefixes:
                            rejected += 1
                            continue
                            
                        if text and any(text.startswith(prefix) for prefix in command_prefixes):
                            rejected += 1
                            continue
                
                # Handle direct message format
                if ('typeMessage' in message and 
                    'textMessage' in message and 
                    'senderName' in message):
                    processed_messages.append(message)
                    continue
                
                # Handle alternative structure
                if 'type' in message and 'message' in message:
                    # Convert to standard format
                    standard_message = {
                        'typeMessage': message.get('type'),
                        'chatId': message.get('chat_id', ''),
                        'senderName': message.get('sender_name', ''),
                        'timestamp': message.get('timestamp', '')
                    }
                    
                    # Add message text if available
                    if message['type'] == 'text' and 'text' in message['message']:
                        standard_message['textMessage'] = message['message']['text']
                    
                    # Add image caption if available
                    elif message['type'] == 'image' and 'caption' in message['message']:
                        standard_message['textMessage'] = message['message']['caption']
                    
                    # Add quote data if available
                    if 'quoted' in message and message['quoted']:
                        standard_message['quotedMessage'] = message['quoted']
                    
                    processed_messages.append(standard_message)
                    continue
                
                # If we couldn't process it in a standard way, append it anyway
                # in debug mode, otherwise skip it
                if self._debug_mode:
                    processed_messages.append(message)
                else:
                    rejected += 1
                
            except Exception as e:
                self.logger.error(f"Error processing message: {str(e)}")
                rejected += 1
        
        self.logger.info(f"Processed {processed} messages, rejected {rejected} messages")
        self.logger.info(f"Returning {len(processed_messages)} processed messages")
        return processed_messages
    
    def _debug_message_structure(self, message: Dict[str, Any], level: str = "DEBUG") -> None:
        """
        Log detailed information about a message structure
        
        Args:
            message (Dict[str, Any]): Message to analyze
            level (str): Log level to use
        """
        log_method = getattr(self.logger, level.lower())
        
        try:
            msg_id = message.get('idMessage', 'Unknown ID')
            message_keys = list(message.keys())
            
            log_method(f"Message {msg_id} keys: {message_keys}")
            
            # Check basic message attributes
            has_sender = 'senderName' in message
            has_text = 'textMessage' in message
            has_timestamp = 'timestamp' in message
            has_type = 'type' in message or 'typeMessage' in message
            has_message_data = 'messageData' in message
            
            log_method(f"Message {msg_id} attributes check:")
            log_method(f"- Has sender: {has_sender}")
            log_method(f"- Has text: {has_text}")
            log_method(f"- Has timestamp: {has_timestamp}")
            log_method(f"- Has type: {has_type}")
            log_method(f"- Has messageData: {has_message_data}")
            
            # If the message has messageData, check its structure
            if has_message_data and isinstance(message['messageData'], dict):
                message_data = message['messageData']
                message_data_keys = list(message_data.keys())
                log_method(f"MessageData keys: {message_data_keys}")
                
                # Check for extended text message data
                if 'extendedTextMessageData' in message_data:
                    log_method(f"ExtendedTextMessageData keys: {list(message_data['extendedTextMessageData'].keys())}")
            
            # Try to extract message type for diagnosis
            msg_type = self._get_message_type(message)
            log_method(f"Detected message type: {msg_type}")
            
            # Check if message type is supported
            is_supported = msg_type in self.supported_message_types if msg_type else False
            log_method(f"Message type is supported: {is_supported}")
            
            # Show text content if available
            if has_text:
                text = message.get('textMessage', '')
                log_method(f"Message text: {text[:50]}{'...' if len(text) > 50 else ''}")
            
            # Check for common rejection reasons
            command_pattern = False
            if has_text and any(message.get('textMessage', '').startswith(prefix) for prefix in self.command_prefixes):
                command_pattern = True
                log_method(f"Message starts with command prefix: {command_pattern}")
                
        except Exception as e:
            log_method(f"Error analyzing message structure: {str(e)}")
            
    def _debug_rejected_message(self, message: Dict[str, Any], index: int) -> None:
        """
        Debug a rejected message to identify the reason for rejection
        
        Args:
            message (Dict[str, Any]): Rejected message
            index (int): Message index
        """
        try:
            msg_id = message.get('idMessage', f'Unknown ID (index: {index})')
            self.logger.info(f"Analyzing rejection reason for message {msg_id}")
            
            # Get message type
            msg_type = self._get_message_type(message)
            
            # Check common rejection reasons
            if not message or not isinstance(message, dict):
                self.logger.info(f"Rejection reason: Not a valid message object")
                return
                
            if msg_type is None:
                self.logger.info(f"Rejection reason: No valid message type detected")
                self._debug_message_structure(message, level="INFO")
                return
                
            if msg_type not in self.supported_message_types:
                self.logger.info(f"Rejection reason: Unsupported message type '{msg_type}'")
                return
                
            # Try to extract text to see if that's the issue
            try:
                text = self._extract_text(message, msg_type)
                if not text and msg_type not in ['imageMessage', 'videoMessage', 'documentMessage', 'audioMessage', 'stickerMessage']:
                    self.logger.info(f"Rejection reason: Empty text in non-media message")
                    return
                    
                if text and any(text.startswith(prefix) for prefix in self.command_prefixes):
                    self.logger.info(f"Rejection reason: Message is a command (starts with {self.command_prefixes})")
                    return
            except Exception as e:
                self.logger.info(f"Rejection reason: Error extracting text: {str(e)}")
                return
                
            # If we got here, the rejection reason is not obvious
            self.logger.info(f"Rejection reason: Unknown (possible bug in processing logic)")
            self._debug_message_structure(message, level="INFO")
            
        except Exception as e:
            self.logger.info(f"Error analyzing rejection reason: {str(e)}")

    def _process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single message
        
        Args:
            message (Dict[str, Any]): Message to process
            
        Returns:
            Optional[Dict[str, Any]]: Processed message or None if message should be ignored
        """
        # Check if the message has basic required fields
        if not message or not isinstance(message, dict):
            self.logger.debug("Skipping message: not a valid message object")
            return None
            
        # Debug output to understand message structure for troubleshooting
        try:
            sender = message.get('senderName', 'Unknown')
            message_id = message.get('idMessage', 'Unknown')
            
            if self._debug_mode:
                self.logger.debug(f"Processing message {message_id} from {sender}")
                # Print message keys for debugging
                self.logger.debug(f"Message keys: {list(message.keys())}")
        except Exception as e:
            if self._debug_mode:
                self.logger.debug(f"Error processing message metadata: {str(e)}")
        
        # DIRECT MESSAGE FORMAT: Check if this is a direct message format (new API structure)
        if 'type' in message and message['type'] in ['incoming', 'outgoing'] and 'textMessage' in message:
            return self._process_direct_message_format(message)
            
        # Handle messages with typeMessage field but without message content (common for media)
        if 'typeMessage' in message and not message.get('textMessage'):
            type_message = message.get('typeMessage', '').lower()
            # Check if this is a media message type
            is_media = any(media_type in type_message for media_type in ['image', 'video', 'audio', 'document', 'sticker'])
            
            if is_media:
                # It's a media message without text - create a placeholder message
                caption = message.get('caption', '')
                media_type = next((mt for mt in ['image', 'video', 'audio', 'document', 'sticker'] 
                                  if mt in type_message), 'media')
                
                # Get timestamp
                timestamp = self._format_timestamp(message.get('timestamp', 0))
                
                # Create a processed message with the media type
                return {
                    'senderName': sender,
                    'textMessage': f"[{media_type.upper()}] {caption}",
                    'timestamp': timestamp,
                    'typeMessage': f"{media_type}Message",
                    'idMessage': message_id
                }
        
        # Get message type
        message_type = self._get_message_type(message)
        
        # Handle different message structures based on type
        if message_type:
            # Check if message type is supported
            if message_type in self.supported_message_types:
                # Try to extract text based on the message type
                text = self._extract_text(message, message_type)
                
                # Skip command messages unless we're in reduced filtering mode
                skip_commands = not self.reduced_filtering
                if skip_commands and text and any(text.startswith(prefix) for prefix in self.command_prefixes):
                    if self._debug_mode:
                        self.logger.debug(f"Skipping command message: {text[:30]}...")
                    return None
                
                # Skip empty messages unless we're in reduced filtering mode
                if not text:
                    if self.reduced_filtering:
                        # Try to construct a meaningful placeholder
                        if message_type == 'imageMessage':
                            text = "[IMAGE]"
                        elif message_type == 'videoMessage':
                            text = "[VIDEO]"
                        elif message_type == 'audioMessage':
                            text = "[AUDIO]"
                        elif message_type == 'documentMessage':
                            text = "[DOCUMENT]"
                        elif message_type == 'stickerMessage':
                            text = "[STICKER]"
                        elif message_type == 'locationMessage':
                            text = "[LOCATION]"
                        elif message_type == 'contactMessage':
                            text = "[CONTACT]"
                        elif message_type == 'reactionMessage':
                            # Try to extract reaction details
                            reaction_text = message.get('messageData', {}).get('reactionMessage', {}).get('reaction', '👍')
                            text = f"[REACTION: {reaction_text}]"
                        else:
                            # Generic non-empty placeholder for any message type
                            text = f"[{message_type.upper()}]"
                    else:
                        if self._debug_mode:
                            self.logger.debug(f"Skipping empty message of type {message_type}")
                        return None
                
                # Format timestamp
                timestamp = self._format_timestamp(message.get('timestamp', 0))
                
                # Create a processed message
                processed = {
                    'senderName': message.get('senderName', 'Unknown'),
                    'textMessage': text,
                    'timestamp': timestamp,
                    'typeMessage': message_type,
                    'idMessage': message.get('idMessage', '')
                }
                
                return processed
            else:
                # Process messages with alternative structure
                return self._process_alternative_structure(message, message_type)
        
        # If no valid message type, check for direct textMessage field
        if 'textMessage' in message and message.get('textMessage'):
            text = message.get('textMessage', '')
            
            # Skip command messages
            if any(text.startswith(prefix) for prefix in self.command_prefixes):
                return None
                
            # Format timestamp
            timestamp = self._format_timestamp(message.get('timestamp', 0))
            
            # Create a processed message
            processed = {
                'senderName': message.get('senderName', 'Unknown'),
                'textMessage': text,
                'timestamp': timestamp,
                'typeMessage': 'textMessage',
                'idMessage': message.get('idMessage', '')
            }
            
            return processed
        
        # In reduced filtering mode, try to salvage any message with a sender
        if self.reduced_filtering and 'senderName' in message:
            # Format timestamp
            timestamp = self._format_timestamp(message.get('timestamp', 0))
            
            # Create a minimal processed message
            processed = {
                'senderName': message.get('senderName', 'Unknown'),
                'textMessage': "[UNKNOWN MESSAGE TYPE]",
                'timestamp': timestamp,
                'typeMessage': 'unknown',
                'idMessage': message.get('idMessage', '')
            }
            
            if self._debug_mode:
                self.logger.debug(f"Salvaged message with unknown type from {processed['senderName']}")
                
            return processed
                
        # If we got here, we couldn't process the message
        if self._debug_mode:
            self.logger.debug(f"Couldn't process message: {message.get('idMessage', 'Unknown ID')}")
        
        return None
    
    def _process_direct_message_format(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a message in the direct format (with type and textMessage directly in the message)
        
        Args:
            message (Dict[str, Any]): Message in direct format
            
        Returns:
            Dict[str, Any]: Processed message
        """
        if self._debug_mode:
            self.logger.debug(f"Processing direct format message: {message.get('idMessage', 'Unknown ID')}")
        
        # Get message text
        text = message.get('textMessage', '')
        
        # Handle special cases like isDeleted
        if message.get('isDeleted', False):
            text = f"[DELETED MESSAGE]"
        elif message.get('isEdited', False):
            text = f"[EDITED] {text}"
            
        # Check for 'typeMessage' which might indicate media
        if 'typeMessage' in message and not text:
            type_message = message.get('typeMessage', '').lower()
            if 'image' in type_message:
                text = "[IMAGE]"
            elif 'video' in type_message:
                text = "[VIDEO]"
            elif 'audio' in type_message:
                text = "[AUDIO]"
            elif 'document' in type_message:
                text = "[DOCUMENT]"
            elif 'sticker' in type_message:
                text = "[STICKER]"
            else:
                text = f"[{type_message.upper()}]"
        
        # Skip command messages
        if text and any(text.startswith(prefix) for prefix in self.command_prefixes):
            if self._debug_mode:
                self.logger.debug("Skipping command message")
            return None
        
        # Format timestamp
        timestamp = self._format_timestamp(message.get('timestamp', 0))
        
        # Create processed message
        processed = {
            'message_id': message.get('idMessage', f'id_{int(time.time()*1000)}'),
            'senderName': message.get('senderName', 'Unknown'),
            'sender': message.get('sender', message.get('chatId', 'unknown')),
            'textMessage': text,
            'timestamp': timestamp,
            'type': message.get('type', 'unknown')
        }
        
        return processed
    
    def _process_alternative_structure(self, message: Dict[str, Any], detected_type: str) -> Optional[Dict[str, Any]]:
        """
        Process a message with a non-standard structure
        
        Args:
            message (Dict[str, Any]): The message to process
            detected_type (str): The detected message type
            
        Returns:
            Optional[Dict[str, Any]]: Processed message or None
        """
        message_data = message.get('messageData', {})
        
        # Extract text based on the type
        text = ""
        type_data = message_data.get(f"{detected_type}Data", {})
        
        if detected_type == 'textMessage':
            text = type_data.get('textMessage', '')
        elif detected_type == 'extendedTextMessage':
            text = type_data.get('text', '')
        elif detected_type in ['imageMessage', 'videoMessage', 'documentMessage', 'audioMessage']:
            caption = type_data.get('caption', '')
            media_type = detected_type.replace('Message', '')
            text = f"[{media_type.upper()}] {caption}"
        
        if not text:
            if self._debug_mode:
                self.logger.debug(f"No text found in alternative structure for {detected_type}")
            return None
            
        # Format timestamp
        timestamp = self._format_timestamp(message.get('timestamp', 0))
        
        # Create processed message
        processed = {
            'message_id': message.get('idMessage', f'id_{int(time.time()*1000)}'),
            'senderName': message.get('senderName', 'Unknown'),
            'sender': message.get('sender', message.get('chatId', 'unknown')),
            'textMessage': text,
            'timestamp': timestamp,
            'type': detected_type
        }
        
        if self._debug_mode:
            self.logger.debug(f"Processed alternative structure: {detected_type}")
            
        return processed

    def _get_message_type(self, message: Dict[str, Any]) -> Optional[str]:
        """
        Get the message type
        
        Args:
            message (Dict[str, Any]): Message
            
        Returns:
            Optional[str]: Message type or None if not found
        """
        # If debug mode, provide more detailed information
        if self._debug_mode:
            # Get all potential places where type could be found
            potential_types = []
            
            if 'type' in message:
                potential_types.append(('message.type', message['type']))
                
            if 'messageData' in message and isinstance(message['messageData'], dict):
                message_data = message['messageData']
                
                if 'type' in message_data:
                    potential_types.append(('message_data.type', message_data['type']))
                
                # Check all supported types
                for msg_type in self.supported_message_types:
                    if msg_type in message_data:
                        potential_types.append((f'message_data.{msg_type}', 'exists'))
                        
            if potential_types:
                self.logger.debug(f"Potential message types: {potential_types}")
        
        # Check for message type in messageData
        if 'messageData' in message:
            message_data = message['messageData']
            
            # Check for type field
            if 'type' in message_data:
                return message_data['type']
            
            # Check for specific message type fields
            for msg_type in self.supported_message_types:
                if msg_type in message_data:
                    return msg_type
                    
            # Check if it's a reaction message
            if 'reactionMessage' in message_data:
                return 'reactionMessage'
                
            # Check for poll messages which might be under a different structure
            if 'pollCreationMessage' in message_data or 'poll' in message_data:
                return 'pollMessageData'
        
        # Sometimes the type is directly in the message (inconsistent API)
        if 'type' in message:
            return message['type']
            
        return None
    
    def _extract_text(self, message: Dict[str, Any], message_type: str) -> str:
        """
        Extract text content from a message
        
        Args:
            message (Dict[str, Any]): Message
            message_type (str): Message type
            
        Returns:
            str: Extracted text
        """
        # Log the extraction attempt
        if self._debug_mode:
            self.logger.debug(f"Extracting text for message type: {message_type}")
            
        try:
            message_data = message.get('messageData', {})
            extracted_text = ""
            
            # For direct API format where fields are at top level
            if 'messageData' not in message and message_type == 'extendedTextMessage':
                # Handle case where extendedTextMessage is directly in the message
                if 'extendedTextMessage' in message:
                    ext_data = message['extendedTextMessage']
                    if isinstance(ext_data, dict) and 'text' in ext_data:
                        return ext_data['text']
                    elif isinstance(ext_data, str):
                        return ext_data
            
            # Check for quoted message
            quoted_message = None
            if message_type == 'extendedTextMessage':
                ext_data = message_data.get('extendedTextMessageData', {})
                if 'quotedMessage' in ext_data:
                    quoted_message = ext_data.get('quotedMessage', {})
                    quoted_text = self._extract_quoted_text(quoted_message)
                    if quoted_text:
                        extracted_text += f"[QUOTE: {quoted_text}] "
            
            # Process by message type
            if message_type == 'textMessage':
                # Check both standard and direct formats
                if 'textMessageData' in message_data:
                    extracted_text += message_data.get('textMessageData', {}).get('textMessage', '')
                elif 'textMessage' in message:
                    # Direct format
                    extracted_text += message.get('textMessage', '')
            
            elif message_type == 'extendedTextMessage':
                # Check both formats - nested and direct
                if 'extendedTextMessageData' in message_data:
                    extracted_text += message_data.get('extendedTextMessageData', {}).get('text', '')
                elif 'extendedTextMessage' in message:
                    ext_data = message.get('extendedTextMessage', {})
                    if isinstance(ext_data, dict):
                        extracted_text += ext_data.get('text', '')
                    elif isinstance(ext_data, str):
                        extracted_text += ext_data
            
            elif message_type in ['imageMessage', 'videoMessage', 'documentMessage', 'audioMessage']:
                # For media messages, extract caption if available
                # Check both formats - nested and direct
                type_data_key = f"{message_type}Data"
                if type_data_key in message_data:
                    media_data = message_data.get(type_data_key, {})
                    caption = media_data.get('caption', '')
                    
                    # Add media type indicator
                    media_type = message_type.replace('Message', '')
                    extracted_text += f"[{media_type.upper()}] {caption}"
                elif message_type in message:
                    media_data = message.get(message_type, {})
                    if isinstance(media_data, dict):
                        caption = media_data.get('caption', '')
                        media_type = message_type.replace('Message', '')
                        extracted_text += f"[{media_type.upper()}] {caption}"
            
            elif message_type == 'stickerMessage':
                extracted_text += "[STICKER]"
                
            elif message_type == 'locationMessage':
                # Handle both formats
                if 'locationMessageData' in message_data:
                    location_data = message_data.get('locationMessageData', {})
                    name = location_data.get('name', 'Unknown location')
                    address = location_data.get('address', '')
                    extracted_text += f"[LOCATION] {name} {address}".strip()
                elif 'locationMessage' in message:
                    location_data = message.get('locationMessage', {})
                    if isinstance(location_data, dict):
                        name = location_data.get('name', 'Unknown location')
                        address = location_data.get('address', '')
                        extracted_text += f"[LOCATION] {name} {address}".strip()
                
            elif message_type == 'contactMessage':
                # Handle both formats
                if 'contactMessageData' in message_data:
                    contact_data = message_data.get('contactMessageData', {})
                    name = contact_data.get('name', 'Unknown contact')
                    extracted_text += f"[CONTACT] {name}"
                elif 'contactMessage' in message:
                    contact_data = message.get('contactMessage', {})
                    if isinstance(contact_data, dict):
                        name = contact_data.get('name', 'Unknown contact')
                        extracted_text += f"[CONTACT] {name}"
                
            elif message_type == 'reactionMessage':
                # Handle both formats
                if 'reactionMessage' in message_data:
                    reaction_data = message_data.get('reactionMessage', {})
                    emoji_text = reaction_data.get('emoji', '👍')
                    
                    # Check if we can get information about the message being reacted to
                    target_msg_id = reaction_data.get('key', {}).get('id', '')
                    if target_msg_id:
                        extracted_text += f"[REACTION: {emoji_text} to message {target_msg_id}]"
                    else:
                        extracted_text += f"[REACTION: {emoji_text}]"
                elif 'reactionMessage' in message:
                    reaction_data = message.get('reactionMessage', {})
                    if isinstance(reaction_data, dict):
                        emoji_text = reaction_data.get('emoji', '👍')
                        target_msg_id = reaction_data.get('key', {}).get('id', '')
                        if target_msg_id:
                            extracted_text += f"[REACTION: {emoji_text} to message {target_msg_id}]"
                        else:
                            extracted_text += f"[REACTION: {emoji_text}]"
            
            # Fallback for direct text handling - in case none of the other formats matched
            if not extracted_text and 'textMessage' in message:
                extracted_text += message.get('textMessage', '')
                
            # Last-resort attempt - if we have typeMessage, use it as a tag
            if not extracted_text and 'typeMessage' in message:
                extracted_text += f"[{message.get('typeMessage', 'MESSAGE').upper()}]"
            
            if self._debug_mode:
                self.logger.debug(f"Extracted text: {extracted_text[:50]}{'...' if len(extracted_text) > 50 else ''}")
                
            return extracted_text
            
        except Exception as e:
            self.logger.warning(f"Error extracting text from message: {str(e)}")
            # Return a non-empty fallback in case of error
            return f"[MESSAGE: {message_type}]"
    
    def _extract_quoted_text(self, quoted_message: Dict[str, Any]) -> str:
        """
        Extract text from a quoted message
        
        Args:
            quoted_message (Dict[str, Any]): Quoted message data
            
        Returns:
            str: Extracted text from quoted message
        """
        # Handle different possible structures of quoted messages
        if not quoted_message:
            return ""
            
        # Check for common message types in quoted message
        quoted_text = ""
        
        # Try to extract from textMessage
        if 'conversation' in quoted_message:
            quoted_text = quoted_message.get('conversation', '')
        
        # Try to extract from extendedTextMessage
        elif 'extendedTextMessageData' in quoted_message:
            quoted_text = quoted_message.get('extendedTextMessageData', {}).get('text', '')
        
        # Try to extract from imageMessage
        elif 'imageMessage' in quoted_message:
            caption = quoted_message.get('imageMessage', {}).get('caption', '')
            quoted_text = f"Image: {caption}" if caption else "Image"
        
        # Try to extract from videoMessage
        elif 'videoMessage' in quoted_message:
            caption = quoted_message.get('videoMessage', {}).get('caption', '')
            quoted_text = f"Video: {caption}" if caption else "Video"
        
        # Try to extract from any known message type
        else:
            for msg_type in ['documentMessage', 'audioMessage', 'stickerMessage', 'locationMessage', 'contactMessage']:
                if msg_type in quoted_message:
                    type_name = msg_type.replace('Message', '').title()
                    caption = quoted_message.get(msg_type, {}).get('caption', '')
                    quoted_text = f"{type_name}: {caption}" if caption else type_name
                    break
        
        return quoted_text
    
    def _format_timestamp(self, timestamp: int) -> str:
        """
        Format a timestamp
        
        Args:
            timestamp (int): Timestamp in seconds since epoch
            
        Returns:
            str: Formatted timestamp
        """
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return 'Unknown time'
    
    def clean_text(self, text: str) -> str:
        """
        Clean text content
        
        Args:
            text (str): Text to clean
            
        Returns:
            str: Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Convert emoji to text representation
        text = emoji.demojize(text)
        
        return text 