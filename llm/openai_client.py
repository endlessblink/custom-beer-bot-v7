#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
OpenAI Client Module

This module provides functionality for interacting with the OpenAI API
to generate summaries of WhatsApp group messages.
"""

import logging
from typing import Any, Dict, List, Optional
import openai
from tenacity import retry, stop_after_attempt, wait_exponential
import os


class OpenAIClient:
    """
    OpenAI Client for generating summaries
    
    This class provides methods for interacting with the OpenAI API.
    """
    
    def __init__(self, 
                 api_key: str, 
                 model: str = "gpt-4", 
                 max_tokens: int = 2000):
        """
        Initialize the OpenAI client
        
        Args:
            api_key (str): OpenAI API key
            model (str, optional): OpenAI model to use. Defaults to "gpt-4".
            max_tokens (int, optional): Maximum tokens for response. Defaults to 2000.
        """
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.client = openai.OpenAI(api_key=api_key)
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"OpenAI client initialized with model {model}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def generate_summary(self, messages: List[Dict[str, Any]], 
                         target_language: str = "hebrew") -> str:
        """
        Generate a summary of messages
        
        Args:
            messages (List[Dict[str, Any]]): List of messages to summarize
            target_language (str, optional): Language for the summary. Defaults to "hebrew".
            
        Returns:
            str: Generated summary
            
        Raises:
            Exception: If summary generation fails
        """
        self.logger.info(f"Generating summary for {len(messages)} messages")
        
        # Prepare messages for the prompt
        formatted_messages = self._format_messages(messages)
        
        # Create the prompt
        prompt = self._create_summary_prompt(formatted_messages, target_language)
        
        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes WhatsApp group conversations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=0.7
            )
            
            # Extract summary from response
            summary = response.choices[0].message.content.strip()
            
            self.logger.info("Summary generated successfully")
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating summary: {str(e)}")
            raise
    
    def _format_messages(self, messages: List[Dict[str, Any]]) -> str:
        """
        Format messages for the prompt
        
        Args:
            messages (List[Dict[str, Any]]): List of messages
            
        Returns:
            str: Formatted messages
        """
        formatted = []
        
        for msg in messages:
            # Extract relevant information
            sender = msg.get('senderName', 'Unknown')
            text = msg.get('textMessage', '')
            timestamp = msg.get('timestamp', '')
            
            # Format message
            formatted.append(f"{sender} ({timestamp}): {text}")
        
        return "\n".join(formatted)
    
    def _create_summary_prompt(self, formatted_messages: str, 
                              target_language: str) -> str:
        """
        Create a prompt for summary generation
        
        Args:
            formatted_messages (str): Formatted messages
            target_language (str): Target language for summary
            
        Returns:
            str: Summary prompt
        """
        summary_prompt = os.environ.get('SUMMARY_PROMPT', '')
        
        if summary_prompt:
            prompt_template = summary_prompt
        else:
            prompt_template = """
צור סיכום מובנה של שיחת קבוצת הוואטסאפ בפורמט הבא:

### סיכום שיחת וואטסאפ

#### 1. נושאים עיקריים שנדונו
- [נושא 1]
- [נושא 2]
- [נושא 3]
(הוסף עד 5 נושאים עיקריים שעלו בשיחה)

#### 2. החלטות או מסקנות חשובות
- [החלטה/מסקנה 1]
- [החלטה/מסקנה 2]
(אם לא נתקבלו החלטות, ציין "לא התקבלו החלטות או מסקנות ברורות בשיחה")

#### 3. הודעות חשובות
- [הודעה חשובה 1] (מאת: [שם השולח אם רלוונטי])
- [הודעה חשובה 2] (מאת: [שם השולח אם רלוונטי])
(אם אין הודעות חשובות ספציפיות, דלג על סעיף זה)

#### 4. משימות או מטלות שהוקצו
- [משימה 1] (אחראי: [שם האחראי אם צוין])
- [משימה 2] (אחראי: [שם האחראי אם צוין])
(אם לא הוקצו משימות, ציין "לא הוקצו משימות ספציפיות בשיחה")

#### 5. אירועים או עדכונים משמעותיים
- [אירוע/עדכון 1]
- [אירוע/עדכון 2]
(אם אין אירועים או עדכונים משמעותיים, דלג על סעיף זה)

הנחיות נוספות:
- הקפד על תמציתיות וברורות בכל נקודה
- אזכר שמות המשתתפים רק כאשר זה רלוונטי להקשר
- שמור על טון ענייני ומקצועי
- אם חלק מהסעיפים ריקים, אפשר לדלג עליהם לחלוטין
- השתמש בשפה רהוטה, ברורה וללא שגיאות
"""
        
        return f"""
הנך מתבקש לסכם את השיחה הבאה מקבוצת WhatsApp ב{target_language}.
{prompt_template}

CONVERSATION:
{formatted_messages}

SUMMARY:
""" 