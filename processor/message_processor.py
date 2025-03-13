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


class MessageProcessor:
    """
    Message Processor for WhatsApp messages
    
    This class provides methods for processing and preparing WhatsApp messages
    for summarization.
    """
    
    def __init__(self, target_language: str = "hebrew"):
        """
        Initialize the message processor
        
        Args:
            target_language (str, optional): Target language for processing. Defaults to "hebrew".
        """
        self.target_language = target_language
        self.logger = logging.getLogger(__name__)
        self.logger.info("Message processor initialized")
        self.debug_mode = False
        
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
    
    def set_debug_mode(self, enabled: bool = True):
        """Enable or disable debug mode"""
        self.debug_mode = enabled
        self.logger.info(f"Debug mode {'enabled' if enabled else 'disabled'}")
        
    def process_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a list of messages
        
        Args:
            messages (List[Dict[str, Any]]): List of messages to process
            
        Returns:
            List[Dict[str, Any]]: Processed messages
        """
        self.logger.info(f"Processing {len(messages)} messages")
        
        processed_messages = []
        rejected_messages = []
        
        for idx, message in enumerate(messages):
            processed = self._process_message(message)
            if processed:
                processed_messages.append(processed)
            else:
                rejected_messages.append(message)
                if self.debug_mode:
                    self.logger.debug(f"Message {idx} rejected: {message.get('idMessage', 'Unknown ID')}")
        
        self.logger.info(f"Processed {len(processed_messages)} messages, rejected {len(rejected_messages)} messages")
        
        if self.debug_mode and rejected_messages:
            rejected_types = {}
            for msg in rejected_messages:
                msg_type = self._get_message_type(msg) or "unknown"
                rejected_types[msg_type] = rejected_types.get(msg_type, 0) + 1
                
            self.logger.debug(f"Rejected message types: {rejected_types}")
            
            if len(processed_messages) == 0:
                self.logger.warning("ALL MESSAGES WERE REJECTED - Check the message processor logic")
        
        return processed_messages
    
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
            
            if self.debug_mode:
                self.logger.debug(f"Processing message {message_id} from {sender}")
                # Print message keys for debugging
                self.logger.debug(f"Message keys: {list(message.keys())}")
        except Exception as e:
            if self.debug_mode:
                self.logger.debug(f"Error processing message metadata: {str(e)}")
        
        # DIRECT MESSAGE FORMAT: Check if this is a direct message format (new API structure)
        if 'type' in message and message['type'] in ['incoming', 'outgoing'] and 'textMessage' in message:
            return self._process_direct_message_format(message)
            
        # Extract message type
        message_type = self._get_message_type(message)
        
        # Debug message type detection
        if self.debug_mode:
            self.logger.debug(f"Detected message type: {message_type}")
        
        # Check message structure if type detection failed
        if not message_type:
            # Dump message structure for debugging (without sensitive content)
            if self.debug_mode:
                self.logger.debug(f"Message keys: {list(message.keys())}")
                if 'messageData' in message:
                    self.logger.debug(f"messageData keys: {list(message['messageData'].keys())}")
                    
                    # Look deeper for potential message types
                    for key, value in message['messageData'].items():
                        if isinstance(value, dict):
                            self.logger.debug(f"{key} keys: {list(value.keys())}")
            
            # SPECIAL CASE: Check if this might be a different message structure
            if 'messageData' in message and isinstance(message['messageData'], dict):
                message_data = message['messageData']
                
                # Check for common types in different structure
                possible_types = ['textMessageData', 'extendedTextMessageData', 'imageMessageData', 
                                 'videoMessageData', 'documentMessageData', 'audioMessageData']
                
                for type_key in possible_types:
                    if type_key in message_data:
                        # Convert to standard type name
                        detected_type = type_key.replace('Data', '')
                        if self.debug_mode:
                            self.logger.debug(f"Alternative type detection: {detected_type}")
                        return self._process_alternative_structure(message, detected_type)
        
        # Skip unsupported message types
        if not message_type or message_type not in self.supported_message_types:
            if self.debug_mode:
                self.logger.debug(f"Skipping message: unsupported type {message_type}")
            return None
        
        # Extract text content
        text = self._extract_text(message, message_type)
        
        # Debug text extraction
        if not text and self.debug_mode:
            self.logger.debug(f"No text extracted from {message_type} message")
        
        # Skip empty messages unless they are media messages
        if not text and message_type not in ['imageMessage', 'videoMessage', 'documentMessage', 'audioMessage', 'stickerMessage']:
            if self.debug_mode:
                self.logger.debug("Skipping message: empty text")
            return None
        
        # Skip command messages
        if text and any(text.startswith(prefix) for prefix in self.command_prefixes):
            if self.debug_mode:
                self.logger.debug("Skipping message: command message")
            return None
        
        # Format timestamp
        timestamp = self._format_timestamp(message.get('timestamp', 0))
        
        # Create processed message
        processed = {
            'senderName': message.get('senderName', 'Unknown'),
            'textMessage': text or f"[{message_type.upper()}]",  # Always have some text representation
            'timestamp': timestamp,
            'type': message_type
        }
        
        return processed
    
    def _process_direct_message_format(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a message in the direct format (with type and textMessage directly in the message)
        
        Args:
            message (Dict[str, Any]): Message in direct format
            
        Returns:
            Dict[str, Any]: Processed message
        """
        if self.debug_mode:
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
            if self.debug_mode:
                self.logger.debug("Skipping command message")
            return None
        
        # Format timestamp
        timestamp = self._format_timestamp(message.get('timestamp', 0))
        
        # Create processed message
        processed = {
            'senderName': message.get('senderName', 'Unknown'),
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
            if self.debug_mode:
                self.logger.debug(f"No text found in alternative structure for {detected_type}")
            return None
            
        # Format timestamp
        timestamp = self._format_timestamp(message.get('timestamp', 0))
        
        # Create processed message
        processed = {
            'senderName': message.get('senderName', 'Unknown'),
            'textMessage': text,
            'timestamp': timestamp,
            'type': detected_type
        }
        
        if self.debug_mode:
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
        if self.debug_mode:
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
        message_data = message.get('messageData', {})
        extracted_text = ""
        
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
            extracted_text += message_data.get('textMessageData', {}).get('textMessage', '')
        
        elif message_type == 'extendedTextMessage':
            extracted_text += message_data.get('extendedTextMessageData', {}).get('text', '')
        
        elif message_type in ['imageMessage', 'videoMessage', 'documentMessage', 'audioMessage']:
            # For media messages, extract caption if available
            type_data_key = f"{message_type}Data"
            media_data = message_data.get(type_data_key, {})
            caption = media_data.get('caption', '')
            
            # Add media type indicator
            media_type = message_type.replace('Message', '')
            extracted_text += f"[{media_type.upper()}] {caption}"
            
        elif message_type == 'stickerMessage':
            extracted_text += "[STICKER]"
            
        elif message_type == 'locationMessage':
            location_data = message_data.get('locationMessageData', {})
            name = location_data.get('name', 'Unknown location')
            address = location_data.get('address', '')
            extracted_text += f"[LOCATION] {name} {address}".strip()
            
        elif message_type == 'contactMessage':
            contact_data = message_data.get('contactMessageData', {})
            name = contact_data.get('name', 'Unknown contact')
            extracted_text += f"[CONTACT] {name}"
            
        elif message_type == 'reactionMessage':
            reaction_data = message_data.get('reactionMessage', {})
            emoji_text = reaction_data.get('emoji', '👍')
            
            # Check if we can get information about the message being reacted to
            target_msg_id = reaction_data.get('key', {}).get('id', '')
            if target_msg_id:
                extracted_text += f"[REACTION: {emoji_text} to message {target_msg_id}]"
            else:
                extracted_text += f"[REACTION: {emoji_text}]"
            
        elif message_type == 'pollMessageData':
            # Try different possible structures for poll messages
            poll_data = (message_data.get('pollCreationMessage', {}) or 
                         message_data.get('poll', {}) or 
                         message_data.get('pollMessageData', {}))
            
            question = poll_data.get('name', '') or poll_data.get('question', '')
            options = poll_data.get('options', [])
            
            if options and isinstance(options, list):
                options_text = ", ".join([opt.get('name', '') for opt in options])
                extracted_text += f"[POLL] {question} - Options: {options_text}"
            else:
                extracted_text += f"[POLL] {question}"
            
        elif message_type in ['buttonResponseMessage', 'listResponseMessage', 'templateButtonReplyMessage']:
            response_data = message_data.get(message_type, {})
            selected_text = (
                response_data.get('selectedDisplayText', '') or 
                response_data.get('selectedButtonId', '') or
                response_data.get('selectedId', '') or
                response_data.get('title', '')
            )
            extracted_text += f"[BUTTON RESPONSE] {selected_text}"
        
        # Try a generic approach for unknown message types
        elif not extracted_text and message_data:
            # Look for common text fields in the message data
            for key in message_data:
                if isinstance(message_data[key], dict):
                    for field in ['text', 'textMessage', 'caption', 'message', 'content']:
                        if field in message_data[key]:
                            extracted_text += message_data[key][field]
        
        return extracted_text
    
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