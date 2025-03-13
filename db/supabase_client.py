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
            # SQL to check if tables exist
            sql_check_tables = """
            SELECT tablename FROM pg_catalog.pg_tables
            WHERE schemaname = 'public';
            """
            
            result = self.client.sql(sql_check_tables).execute()
            existing_tables = [table['tablename'] for table in result.data]
            
            self.logger.info(f"Existing tables: {existing_tables}")
            
            # Create messages table if it doesn't exist
            if 'messages' not in existing_tables:
                self.logger.info("Creating messages table")
                sql_create_messages = """
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
                """
                self.client.sql(sql_create_messages).execute()
            
            # Create summaries table if it doesn't exist
            if 'summaries' not in existing_tables:
                self.logger.info("Creating summaries table")
                sql_create_summaries = """
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
                """
                self.client.sql(sql_create_summaries).execute()
            
            # Check table structure and alter if needed
            if 'summaries' in existing_tables:
                # Check if end_time column exists
                sql_check_column = """
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'summaries' AND column_name = 'end_time';
                """
                result = self.client.sql(sql_check_column).execute()
                
                if not result.data:
                    self.logger.info("Adding end_time column to summaries table")
                    sql_add_column = """
                    ALTER TABLE summaries 
                    ADD COLUMN IF NOT EXISTS end_time TIMESTAMP WITH TIME ZONE;
                    """
                    self.client.sql(sql_add_column).execute()
                
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
            
            data = {
                'group_id': message.get('group_id', ''),
                'sender_id': message.get('sender_id', ''),
                'sender_name': message.get('senderName', 'Unknown'),
                'message_text': message.get('textMessage', ''),
                'timestamp': timestamp.isoformat(),
                'message_type': message.get('type', 'text')
            }
            
            result = self.client.table('messages').insert(data).execute()
            self.logger.info(f"Message stored with ID: {result.data[0]['id']}")
            return result.data[0]
            
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