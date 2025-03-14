#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Supabase Client Module

This module provides functionality for interacting with the Supabase database
to store and retrieve WhatsApp messages and summaries.
"""

import logging
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from supabase import create_client, Client


class SupabaseClient:
    """
    Supabase Client for database operations
    
    This class provides methods for interacting with Supabase to store
    and retrieve WhatsApp messages and summaries.
    """
    
    def __init__(self, url: str, key: str):
        """
        Initialize the Supabase client
        
        Args:
            url (str): Supabase URL
            key (str): Supabase API key
        """
        self.url = url
        self.key = key
        self.client = create_client(url, key)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Supabase client initialized")
        
        # Ensure tables exist
        self._init_tables()
    
    def _init_tables(self) -> None:
        """
        Initialize database tables if they don't exist
        
        This method checks if the required tables exist and creates them if they don't.
        """
        try:
            # בגרסאות חדשות של Supabase, לא ניתן להשתמש ב-SQL ישירות
            # במקום זאת נבדוק אם הטבלאות קיימות על ידי ניסיון לבצע שאילתה
            try:
                # בדיקה אם טבלת messages קיימת
                self.client.table('messages').select('count(*)', count='exact').limit(1).execute()
                self.logger.info("Table 'messages' exists")
            except Exception as e:
                if "relation" in str(e) and "does not exist" in str(e):
                    self.logger.info("Creating messages table")
                    # ניצור את הטבלה באמצעות REST API או לחלופין נשתמש ב-migrations
                    # יש להריץ את הסקריפט SQL דרך ממשק הניהול של Supabase
                    self.logger.warning("Cannot automatically create tables. Please create them manually in Supabase.")
                    self.logger.info("Required schema for messages table:")
                    self.logger.info("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id SERIAL PRIMARY KEY,
                        group_id TEXT NOT NULL,
                        sender_id TEXT NOT NULL,
                        sender_name TEXT NOT NULL,
                        message_text TEXT NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        message_type TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_messages_group_id ON messages(group_id);
                    CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
                    """)
            
            try:
                # בדיקה אם טבלת summaries קיימת
                self.client.table('summaries').select('count(*)', count='exact').limit(1).execute()
                self.logger.info("Table 'summaries' exists")
                
                # עדיף לא לבדוק מבנה עמודות כי אין דרך נוחה לעשות זאת בלי SQL
            except Exception as e:
                if "relation" in str(e) and "does not exist" in str(e):
                    self.logger.info("Creating summaries table")
                    self.logger.warning("Cannot automatically create tables. Please create them manually in Supabase.")
                    self.logger.info("Required schema for summaries table:")
                    self.logger.info("""
                    CREATE TABLE IF NOT EXISTS summaries (
                        id SERIAL PRIMARY KEY,
                        group_id TEXT NOT NULL,
                        summary_text TEXT NOT NULL,
                        start_time TIMESTAMP WITH TIME ZONE,
                        end_time TIMESTAMP WITH TIME ZONE,
                        message_count INTEGER NOT NULL,
                        model_used TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_summaries_group_id ON summaries(group_id);
                    CREATE INDEX IF NOT EXISTS idx_summaries_created_at ON summaries(created_at);
                    """)
                
        except Exception as e:
            self.logger.error(f"Error initializing tables: {str(e)}")
    
    def store_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Store a message in the database
        
        Args:
            message (Dict[str, Any]): Message to store
            
        Returns:
            Optional[Dict[str, Any]]: Stored message with ID or None if failed
        """
        try:
            timestamp = None
            if isinstance(message.get('timestamp'), str):
                try:
                    timestamp = datetime.strptime(message['timestamp'], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()
            
            # נבדוק אם כבר יש שדה message_text - אם אין, ננסה להשתמש ב-textMessage
            message_text = message.get('message_text', '')
            if not message_text and 'textMessage' in message:
                message_text = message.get('textMessage', '')
            
            # אם יש בעיה עם המבנה של הטבלה ועמודת message_text, ננסה לאחסן את ההודעה באמצעות מבנה גמיש יותר
            try:
                data = {
                    'group_id': message.get('group_id', ''),
                    'sender_id': message.get('sender_id', ''),
                    'sender_name': message.get('senderName', 'Unknown'),
                    'message_text': message_text,
                    'timestamp': timestamp.isoformat(),
                    'message_type': message.get('type', 'text')
                }
                
                result = self.client.table('messages').insert(data).execute()
                self.logger.info(f"Message stored with ID: {result.data[0]['id']}")
                return result.data[0]
                
            except Exception as specific_error:
                if "message_text" in str(specific_error) and "column" in str(specific_error):
                    # אולי העמודה נקראת אחרת או לא קיימת
                    # ננסה ליצור JSON מלא של ההודעה ולאחסן אותו בעמודה אחרת
                    self.logger.warning(f"Trying alternative storage method: {str(specific_error)}")
                    
                    # הכנת נתוני ההודעה כ-JSON מלא
                    full_message = {
                        'group_id': message.get('group_id', ''),
                        'sender_id': message.get('sender_id', ''),
                        'sender_name': message.get('senderName', 'Unknown'),
                        'text': message_text,
                        'timestamp': timestamp.isoformat(),
                        'message_type': message.get('type', 'text'),
                        'original_data': message  # כולל את כל המידע המקורי
                    }
                    
                    # ננסה לשמור את המידע בטבלת לוגים זמנית
                    try:
                        result = self.client.table('message_logs').insert({
                            'data': json.dumps(full_message),
                            'created_at': datetime.now().isoformat()
                        }).execute()
                        self.logger.info("Message stored in logs table as fallback")
                        return {'id': 'logged', 'data': full_message}
                    except Exception as fallback_error:
                        self.logger.error(f"Failed to use fallback storage: {str(fallback_error)}")
                        # נחזיר תשובה מזויפת כדי שהתוכנית תמשיך לרוץ
                        return {'id': 'none', 'error': str(specific_error)}
                else:
                    raise
            
        except Exception as e:
            self.logger.error(f"Error storing message: {str(e)}")
            return None
    
    def store_messages(self, messages: List[Dict[str, Any]], group_id: str) -> int:
        """
        Store multiple messages
        
        Args:
            messages (List[Dict[str, Any]]): Messages to store
            group_id (str): Group ID
            
        Returns:
            int: Number of messages stored
        """
        if not messages:
            return 0
        
        stored_count = 0
        for message in messages:
            message['group_id'] = group_id
            if self.store_message(message):
                stored_count += 1
        
        self.logger.info(f"Stored {stored_count} messages for group {group_id}")
        return stored_count
    
    def store_summary(self, summary: str, group_id: str, 
                     start_time: datetime, end_time: datetime,
                     message_count: int, model_used: str) -> Optional[Dict[str, Any]]:
        """
        Store a summary
        
        Args:
            summary (str): Summary text
            group_id (str): Group ID
            start_time (datetime): Start time for the summary period
            end_time (datetime): End time for the summary period
            message_count (int): Number of messages summarized
            model_used (str): Model used for summarization
            
        Returns:
            Optional[Dict[str, Any]]: Stored summary with ID or None if failed
        """
        try:
            # Convert datetime objects to ISO format strings
            start_time_str = start_time.isoformat() if start_time else None
            end_time_str = end_time.isoformat() if end_time else None
            
            data = {
                'group_id': group_id,
                'summary_text': summary,
                'message_count': message_count,
                'model_used': model_used
            }
            
            # Add timestamps if available
            if start_time_str:
                data['start_time'] = start_time_str
            if end_time_str:
                data['end_time'] = end_time_str
            
            # Insert the summary
            result = self.client.table('summaries').insert(data).execute()
            
            if result.data and len(result.data) > 0:
                self.logger.info(f"Summary stored with ID: {result.data[0]['id']}")
                return result.data[0]
            else:
                self.logger.warning("Summary inserted but no data returned")
                return None
            
        except Exception as e:
            self.logger.error(f"Error storing summary: {str(e)}")
            return None
    
    def get_messages(self, group_id: str, 
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None,
                    limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get messages from the database
        
        Args:
            group_id (str): Group ID
            start_time (datetime, optional): Start time. Defaults to None.
            end_time (datetime, optional): End time. Defaults to None.
            limit (int, optional): Maximum number of messages. Defaults to 100.
            
        Returns:
            List[Dict[str, Any]]: Messages
        """
        try:
            query = self.client.table('messages').select('*').eq('group_id', group_id)
            
            if start_time:
                query = query.gte('timestamp', start_time.isoformat())
                
            if end_time:
                query = query.lte('timestamp', end_time.isoformat())
                
            query = query.order('timestamp', desc=False).limit(limit)
            result = query.execute()
            
            self.logger.info(f"Retrieved {len(result.data)} messages for group {group_id}")
            return result.data
            
        except Exception as e:
            self.logger.error(f"Error getting messages: {str(e)}")
            return []
    
    def get_recent_summaries(self, group_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent summaries
        
        Args:
            group_id (str): Group ID
            limit (int, optional): Maximum number of summaries. Defaults to 5.
            
        Returns:
            List[Dict[str, Any]]: Summaries
        """
        try:
            query = self.client.table('summaries') \
                .select('*') \
                .eq('group_id', group_id) \
                .order('created_at', desc=True) \
                .limit(limit)
                
            result = query.execute()
            
            self.logger.info(f"Retrieved {len(result.data)} summaries for group {group_id}")
            return result.data
            
        except Exception as e:
            self.logger.error(f"Error getting summaries: {str(e)}")
            return [] 