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
        
        # Validate input
        if not messages:
            error_msg = "Cannot generate summary: No messages provided"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Validate minimum message count for a meaningful summary
        if len(messages) < 3:
            self.logger.warning(f"Very few messages ({len(messages)}) provided for summarization")
            
            # Instead of failing, provide a warning in the logs but proceed
            if len(messages) == 1:
                self.logger.info("Only one message provided, proceeding with simple formatting")
                # For a single message, just return it directly with a header
                try:
                    sender = messages[0].get('senderName', 'Unknown')
                    text = messages[0].get('textMessage', '')
                    if text:
                        return f"### סיכום הודעה בודדת\n\n{sender}: {text}"
                    else:
                        error_msg = "The single message provided has no text content"
                        self.logger.error(error_msg)
                        raise ValueError(error_msg)
                except Exception as e:
                    error_msg = f"Error handling single message case: {str(e)}"
                    self.logger.error(error_msg)
                    raise ValueError(error_msg)
        
        # Log the type of messages for debugging
        try:
            self.logger.debug(f"Sample message keys: {list(messages[0].keys())}")
            self.logger.debug(f"Sample message sender: {messages[0].get('senderName', 'N/A')}")
            self.logger.debug(f"Sample message text: {messages[0].get('textMessage', '')[:50]}...")
        except (IndexError, KeyError, TypeError) as e:
            self.logger.warning(f"Could not log sample message info: {str(e)}")
        
        # Prepare messages for the prompt
        formatted_messages = self._format_messages(messages)
        
        # Validate formatted messages
        if not formatted_messages or formatted_messages.strip() == "":
            error_msg = "Failed to format messages for summary"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Check if the formatted messages exceed any token limits
        token_estimate = len(formatted_messages) / 4  # Rough estimate: ~4 chars per token
        if token_estimate > 32000:  # Conservative limit for GPT-4 input tokens
            self.logger.warning(f"Input may exceed token limit ({int(token_estimate)} estimated tokens)")
            # Truncate to approximately 30K tokens for safety
            formatted_messages = formatted_messages[:120000]  # ~30K tokens
            self.logger.info(f"Truncated input to {len(formatted_messages)} characters")
        
        # Create the prompt
        prompt = self._create_summary_prompt(formatted_messages, target_language)
        
        try:
            # Call OpenAI API
            self.logger.info(f"Calling OpenAI API with model {self.model}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes WhatsApp group conversations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=0.7
            )
            
            # Validate response
            if not response or not hasattr(response, 'choices') or not response.choices:
                error_msg = "OpenAI API returned an invalid response format"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Extract summary from response
            summary = response.choices[0].message.content.strip()
            
            # Validate summary
            if not summary:
                error_msg = "OpenAI API returned an empty summary"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            
            self.logger.info("Summary generated successfully")
            return summary
            
        except openai.APIError as e:
            error_msg = f"OpenAI API error: {str(e)}"
            self.logger.error(error_msg)
            # Add request details to help diagnose the issue
            self.logger.error(f"Request details: model={self.model}, max_tokens={self.max_tokens}")
            raise openai.APIError(f"{error_msg}. Please check your API key and OpenAI service status.")

        except openai.RateLimitError as e:
            error_msg = f"OpenAI rate limit exceeded: {str(e)}"
            self.logger.error(error_msg)
            raise openai.RateLimitError(f"{error_msg}. Please wait a few minutes before trying again.")

        except openai.APIConnectionError as e:
            error_msg = f"Failed to connect to OpenAI API: {str(e)}"
            self.logger.error(error_msg)
            raise openai.APIConnectionError(f"{error_msg}. Please check your internet connection.")

        except openai.InvalidRequestError as e:
            error_msg = f"Invalid request to OpenAI API: {str(e)}"
            self.logger.error(error_msg)
            # Log additional details about the request
            self.logger.error(f"Request details: model={self.model}, prompt_length={len(prompt)}")
            
            # Check for common issues
            if "maximum context length" in str(e).lower():
                raise openai.InvalidRequestError(f"{error_msg}. The input is too long for the model. Try summarizing fewer messages.")
            elif "rate limit" in str(e).lower():
                raise openai.InvalidRequestError(f"{error_msg}. You may have hit a rate limit. Please wait and try again.")
            else:
                raise openai.InvalidRequestError(f"{error_msg}. Please check your request parameters.")

        except Exception as e:
            error_msg = f"Unexpected error during summary generation: {str(e)}"
            self.logger.error(error_msg)
            # Log the exception type to help with debugging
            self.logger.error(f"Exception type: {type(e).__name__}")
            raise Exception(f"Failed to generate summary: {str(e)}. Please check the logs for more details.")
    
    def _format_messages(self, messages: List[Dict[str, Any]]) -> str:
        """
        Format messages for the prompt
        
        Args:
            messages (List[Dict[str, Any]]): List of messages
            
        Returns:
            str: Formatted messages
        """
        formatted = []
        skipped = 0
        
        self.logger.info(f"Formatting {len(messages)} messages for prompt")
        
        for i, msg in enumerate(messages):
            try:
                # Validate the message
                if not isinstance(msg, dict):
                    self.logger.warning(f"Skipping message {i}: Not a dictionary")
                    skipped += 1
                    continue
                    
                # Extract relevant information
                sender = msg.get('senderName', 'Unknown')
                text = msg.get('textMessage', '')
                timestamp = msg.get('timestamp', '')
                
                # Validate text content
                if not text or not isinstance(text, str):
                    self.logger.debug(f"Message {i} has empty or invalid text: {text}")
                    text = "[EMPTY MESSAGE]"
                    
                # Validate sender
                if not sender or not isinstance(sender, str):
                    self.logger.debug(f"Message {i} has invalid sender: {sender}")
                    sender = "Unknown"
                    
                # Format message
                formatted_msg = f"{sender} ({timestamp}): {text}"
                self.logger.debug(f"Formatted message {i}: {formatted_msg[:50]}...")
                formatted.append(formatted_msg)
                
            except Exception as e:
                self.logger.warning(f"Error formatting message {i}: {str(e)}")
                skipped += 1
        
        # Log statistics
        if skipped > 0:
            self.logger.warning(f"Skipped {skipped} messages during formatting")
        self.logger.info(f"Successfully formatted {len(formatted)} messages")
        
        # Check if we have any messages after formatting
        if not formatted:
            self.logger.warning("No messages were successfully formatted")
            return "No valid messages to summarize."
        
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