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
from datetime import datetime


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
    def generate_summary(self, 
                         messages: List[Dict[str, Any]],
                         target_language: str = 'hebrew') -> str:
        """
        Generate a summary of WhatsApp messages
        
        Args:
            messages (List[Dict[str, Any]]): List of messages
            target_language (str, optional): Target language for the summary. Defaults to 'hebrew'.
            
        Returns:
            str: Summary text
        """
        if not messages:
            logging.warning("No messages provided for summary generation")
            return "No messages to summarize"
            
        logging.info(f"Generating summary for {len(messages)} messages")
        
        # Add cache-busting timestamp to ensure we get a fresh summary every time
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        cache_busting_id = os.urandom(4).hex()
        logging.info(f"Adding cache-busting timestamp: {current_time} and ID: {cache_busting_id}")
        
        # Diagnostic logging
        message_types = {}
        for msg in messages:
            msg_type = msg.get('typeMessage', 'unknown')
            message_types[msg_type] = message_types.get(msg_type, 0) + 1
        
        logging.info(f"Message types in input: {message_types}")
        
        # Format messages for the prompt
        formatted_messages = self._format_messages_for_summary(messages)
        
        # Calculate token count (rough estimation)
        token_count = len(formatted_messages) // 4  # Very rough approximation
        logging.info(f"Estimated token count for messages: {token_count}")
        
        # Check if we have a reasonable amount of content
        if len(formatted_messages) < 100:  # This is an arbitrary threshold
            logging.warning(f"Very little content for summary: only {len(formatted_messages)} characters")
            if len(messages) >= 20:  # If we have messages but little formatted content
                logging.warning("Many messages but little formatted content. This might indicate filtering or formatting issues.")
        
        # Create prompt based on target language
        prompt = self._create_summary_prompt(formatted_messages, target_language)
        
        # Add the cache-busting info as a hidden instruction to the prompt
        # This will be invisible in the output but ensures a unique request each time
        anti_cache_instruction = f"\n\n[INTERNAL NOTE: Request Time: {current_time}, ID: {cache_busting_id}. This is a new, fresh summary request. Ignore this timestamp in your summary.]"
        prompt += anti_cache_instruction
        
        # Call OpenAI API and get the summary
        try:
            # Check for extremely low token count which might indicate a problem
            if token_count < 50 and len(messages) > 10:
                logging.warning("Very low token count despite having messages. This might indicate a formatting problem.")
                # Add a diagnostic message to the prompt
                prompt += f"\n\nWARNING: The input seems unusually small for {len(messages)} messages. Please extract ANY meaningful information that can be found."
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that generates concise and accurate summaries of WhatsApp group conversations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=0.7
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Post-processing checks
            if "לא דווח" in summary and summary.count("לא דווח") > 5:
                # If many "not reported" instances, log a warning
                logging.warning("Summary contains many 'not reported' entries, which might indicate a problem with content extraction")
            
            if len(summary) < 100:
                logging.warning(f"Generated summary is very short ({len(summary)} chars), which might indicate a problem")
            
            # Remove empty sections from the summary
            summary = self._remove_empty_sections(summary)
            
            return summary
            
        except Exception as e:
            logging.error(f"Error generating summary: {str(e)}")
            return f"Error generating summary: {str(e)}"

    def _format_messages_for_summary(self, messages: List[Dict[str, Any]]) -> str:
        """
        Format messages for summary generation
        
        Args:
            messages (List[Dict[str, Any]]): List of messages
            
        Returns:
            str: Formatted messages string
        """
        formatted_messages = []
        
        logging.info(f"Formatting {len(messages)} messages for summary")
        
        # Sort messages by timestamp if available
        try:
            messages_with_timestamp = [
                msg for msg in messages 
                if 'timestamp' in msg and msg['timestamp'] is not None
            ]
            
            if messages_with_timestamp:
                # Handle different timestamp formats - ensure they're converted to integers
                for msg in messages_with_timestamp:
                    if isinstance(msg['timestamp'], str):
                        try:
                            # Try to convert string timestamp to integer
                            msg['timestamp'] = int(msg['timestamp'])
                            logging.info(f"Converted string timestamp '{msg['timestamp']}' to integer")
                        except ValueError:
                            # If conversion fails, log but keep the message
                            logging.warning(f"Could not convert timestamp '{msg['timestamp']}' to integer, using as is")
                
                # Sort by timestamp, handling both integer and string timestamps
                def get_timestamp_value(msg):
                    ts = msg.get('timestamp')
                    if isinstance(ts, int):
                        return ts
                    elif isinstance(ts, str):
                        try:
                            return int(ts)
                        except ValueError:
                            return 0  # Default value if conversion fails
                    return 0
                
                messages_with_timestamp.sort(key=get_timestamp_value)
                messages = messages_with_timestamp
                logging.info(f"Sorted {len(messages_with_timestamp)} messages by timestamp")
            else:
                logging.warning("No messages with timestamp found for sorting")
        except Exception as e:
            logging.warning(f"Error sorting messages by timestamp: {str(e)}")
            logging.warning(f"Timestamp example: {messages[0].get('timestamp') if messages else 'No messages'}")
        
        filtered_count = 0
        error_count = 0
        
        for msg_index, msg in enumerate(messages):
            try:
                # Extract message data
                timestamp = msg.get('timestamp')
                
                # Handle different timestamp formats
                time_str = "Unknown time"
                if timestamp is not None:
                    try:
                        if isinstance(timestamp, int):
                            time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                        elif isinstance(timestamp, str):
                            # Try to convert string to int first
                            try:
                                time_str = datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                # If that fails, just use the string as is
                                time_str = timestamp
                        elif isinstance(timestamp, datetime):
                            # If it's already a datetime object
                            time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception as time_error:
                        logging.error(f"Error formatting timestamp {timestamp} (type: {type(timestamp)}): {str(time_error)}")
                        time_str = f"Time error ({type(timestamp).__name__})"
                
                sender = msg.get('senderName', 'Unknown')
                
                # Handle different message types
                msg_type = msg.get('typeMessage')
                
                if msg_type == 'textMessage':
                    text = msg.get('textMessage', '')
                    if text:
                        formatted_messages.append(f"[{time_str}] {sender}: {text}")
                    else:
                        filtered_count += 1
                
                elif msg_type == 'imageMessage':
                    caption = msg.get('caption', '(image)')
                    formatted_messages.append(f"[{time_str}] {sender}: [IMAGE] {caption}")
                
                elif msg_type == 'videoMessage':
                    caption = msg.get('caption', '(video)')
                    formatted_messages.append(f"[{time_str}] {sender}: [VIDEO] {caption}")
                
                elif msg_type == 'documentMessage':
                    filename = msg.get('fileName', '(document)')
                    formatted_messages.append(f"[{time_str}] {sender}: [DOCUMENT] {filename}")
                
                elif msg_type == 'audioMessage':
                    formatted_messages.append(f"[{time_str}] {sender}: [AUDIO MESSAGE]")
                
                elif msg_type == 'locationMessage':
                    latitude = msg.get('latitude', 'unknown')
                    longitude = msg.get('longitude', 'unknown')
                    formatted_messages.append(f"[{time_str}] {sender}: [LOCATION] Lat: {latitude}, Lon: {longitude}")
                
                elif msg_type == 'contactMessage':
                    display_name = msg.get('displayName', '(contact)')
                    formatted_messages.append(f"[{time_str}] {sender}: [CONTACT] {display_name}")
                
                elif msg_type == 'extendedTextMessage':
                    # Try to extract text from extended message
                    text = msg.get('extendedTextMessage', {}).get('text', '')
                    if not text and 'textMessage' in msg:
                        text = msg.get('textMessage', '')
                    
                    # Check for quoted message
                    quoted_msg = msg.get('quotedMessage', {})
                    quoted_text = quoted_msg.get('textMessage', '') if quoted_msg else ''
                    
                    if quoted_text:
                        formatted_messages.append(f"[{time_str}] {sender} replying to '{quoted_text[:30]}...': {text}")
                    else:
                        formatted_messages.append(f"[{time_str}] {sender}: {text}")
                
                else:
                    # For unknown message types, try to extract any available content
                    # Look for common text fields
                    text = ''
                    for field in ['textMessage', 'text', 'caption', 'message', 'content']:
                        if field in msg and msg[field]:
                            text = msg[field]
                            break
                    
                    if text:
                        formatted_messages.append(f"[{time_str}] {sender}: {text}")
                    else:
                        # If no text field found, include a placeholder with message type
                        formatted_messages.append(f"[{time_str}] {sender}: [MESSAGE TYPE: {msg_type or 'UNKNOWN'}]")
                        logging.debug(f"Unknown message type: {msg_type}, keys: {list(msg.keys())}")
            
            except Exception as e:
                error_count += 1
                logging.error(f"Error formatting message {msg_index} for summary: {str(e)}")
                logging.debug(f"Problematic message: {msg}")
                # Try a simplified approach to salvage the message
                try:
                    sender = msg.get('senderName', 'Unknown')
                    # Look for any text content
                    text_content = ''
                    for field in ['textMessage', 'text', 'caption', 'message', 'content']:
                        if field in msg and msg[field]:
                            text_content = msg[field]
                            break
                    
                    if text_content:
                        formatted_messages.append(f"[Error formatting time] {sender}: {text_content}")
                        logging.info(f"Salvaged message with text: {text_content[:30]}...")
                except Exception as rescue_error:
                    logging.error(f"Could not salvage message: {str(rescue_error)}")
                continue
        
        logging.info(f"Formatted {len(formatted_messages)} messages, filtered {filtered_count} messages, encountered {error_count} errors")
        
        formatted_text = "\n".join(formatted_messages)
        
        # Final check to ensure we have content
        if not formatted_text:
            logging.warning("NO FORMATTED MESSAGES GENERATED. Last resort attempt to extract any text:")
            # Last resort attempt to extract any usable text
            for msg in messages:
                try:
                    # Try to extract sender
                    sender = msg.get('senderName', 'Unknown')
                    
                    # Try to find any text field
                    for field in msg:
                        if isinstance(msg[field], str) and len(msg[field]) > 2:
                            formatted_messages.append(f"{sender}: {msg[field]}")
                            logging.info(f"Added emergency text from field '{field}': {msg[field][:30]}...")
                            break
                except Exception as e:
                    logging.error(f"Error in emergency text extraction: {str(e)}")
            
            formatted_text = "\n".join(formatted_messages)
            logging.info(f"Emergency text extraction produced {len(formatted_messages)} lines")
            
        return formatted_text
    
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

            # עדכון בשביל קבוצת Custom Beer Node - תבנית ספציפית יותר עם כותרות רלוונטיות
            custom_beer_prompt = """
## סיכום שיחות קבוצת Custom Beer Node
### תאריך: [תאריך] | תקופה: [שעה מהודעה ראשונה] - [שעה מהודעה אחרונה]

### 😂 בדיחת AI היום:
[הוסף כאן בדיחה קצרה הקשורה לבינה מלאכותית]

### 1. פרויקטים ופיתוחים שהוצגו
- [פרויקט 1 + תיאור קצר] (מאת: [שם המציג])
- [פרויקט 2 + תיאור קצר] (מאת: [שם המציג])
- ...

### 2. תוצרים ודמואים שהוצגו
- [תוצר 1 + תיאור] (מאת: [שם המציג])
- [תוצר 2 + תיאור] (מאת: [שם המציג])
- ...

### 3. כלים וטכנולוגיות חדשים שנדונו
- [כלי/טכנולוגיה 1 + תיאור קצר]
- [כלי/טכנולוגיה 2 + תיאור קצר]
- ...

### 4. בעיות טכניות ופתרונות שהוצעו
- [בעיה 1]: [פתרון שהוצע]
- [בעיה 2]: [פתרון שהוצע]
- ...

### 5. משאבים ומאמרים שהועברו
- [קישור/מאמר 1]: [תיאור קצר] (שותף ע"י: [שם])
- [קישור/מאמר 2]: [תיאור קצר] (שותף ע"י: [שם])
- ...

### 6. סטטוס פרויקטים מתמשכים
- [פרויקט 1]: [סטטוס עדכני] (מאת: [שם])
- [פרויקט 2]: [סטטוס עדכני] (מאת: [שם])
- ...

### 7. שאלות פתוחות ותחומי עניין לעתיד
- [שאלה/נושא 1]
- [שאלה/נושא 2]
- ...

### 8. חידושים בתחום בינה מלאכותית גנרטיבית
- [חידוש 1 + תיאור קצר]
- [חידוש 2 + תיאור קצר]
- ...

### 9. ווקפלואים (workflows) של ComfyUI שהועברו
- [ווקפלו 1 + תיאור] (מאת: [שם])
- [ווקפלו 2 + תיאור] (מאת: [שם])
- ...

### 10. מושגים טכניים חדשים שנדונו
- [מושג 1]: [הסבר קצר]
- [מושג 2]: [הסבר קצר]
- ...
"""

            # החלף את התבנית הכללית בתבנית המותאמת לקבוצה
            prompt_template = custom_beer_prompt

        # הנחיות מיוחדות לסיכום כדי לתת למודל הבנה טובה יותר של המשימה
        better_instruction = f"""
הנך מתבקש לסכם את השיחה הבאה מקבוצת WhatsApp ב{target_language}.

הערות חשובות:
1. עליך לחפש ולהתייחס באופן אקטיבי לכל התוכן בהודעות, גם אם מדובר בפרטים קטנים
2. אל תחזיר תבנית ריקה עם "לא דווח" בכל הסעיפים - אם יש תוכן כלשהו, צרף אותו תחת הקטגוריה המתאימה
3. אם יש תוכן שאינו מתאים לקטגוריות הקיימות, הוסף הערה בסוף הסיכום
4. אם סעיף מסוים אכן ריק, רשום "לא דווח" רק עבורו, ולא עבור כל הסעיפים
5. אם מוזכר תוכן או קישור כלשהו, כלול אותו בסיכום
6. חשוב מאוד: עליך לסכם את כל המידע המהותי, גם אם מופיע רק פעם אחת בשיחה
7. אם יש תכנים דומים שחוזרים על עצמם, אחד אותם תחת סעיף אחד

{prompt_template}

כעת נמצאות בפניך ההודעות לסיכום. יש בסך הכל כ-[מספר] הודעות, חלקן אינפורמטיביות וחלקן פחות.
בכל מקרה, עליך לסרוק את כל ההודעות ולסכם את כל המידע המהותי שנמצא בהן.

CONVERSATION:
{formatted_messages}

SUMMARY:
"""

        # החלף את המילה [מספר] במספר המשוער של ההודעות
        message_count = formatted_messages.count('\n') + 1  # הערכה גסה של מספר ההודעות
        better_instruction = better_instruction.replace('[מספר]', str(message_count))
        
        return better_instruction

    def _create_single_message_summary_prompt(self, formatted_message: str, sender: str, text: str, 
                                            target_language: str) -> str:
        """
        Create a prompt specifically for single message summary with context
        
        Args:
            formatted_message (str): Formatted single message
            sender (str): Message sender
            text (str): Message text
            target_language (str): Target language for summary
            
        Returns:
            str: Summary prompt
        """
        return f"""
הנך מתבקש לסכם הודעה בודדת מקבוצת WhatsApp ב{target_language}.

ההודעה היא:
{sender}: {text}

אני מבקש:
1. לכתוב סיכום להודעה הבודדת
2. במידה ולא ניתן להבין את ההקשר המלא, יש להציע הקשר אפשרי או הסבר כללי למשמעות ההודעה
3. במקרה שההודעה לא ברורה, עליך להדגיש שזוהי הודעה בודדת ללא הקשר קודם

יש לפרמט את הסיכום כך:

### סיכום הודעה בודדת

**הודעה:**
{sender}: {text}

**ניתוח והסבר:**
[כאן יש לכתוב ניתוח קצר של ההודעה - מה היא אומרת, למה היא עשויה להתייחס, או מה אפשר להבין ממנה]

SUMMARY:
"""

    def _create_two_message_summary_prompt(self, formatted_messages: str, target_language: str) -> str:
        """
        Create a prompt specifically for summarizing a two-message conversation
        
        Args:
            formatted_messages (str): Formatted messages
            target_language (str): Target language for summary
            
        Returns:
            str: Summary prompt
        """
        return f"""
הנך מתבקש לסכם שיחה קצרה בת שתי הודעות מקבוצת WhatsApp ב{target_language}.

השיחה הקצרה היא:
{formatted_messages}

אני מבקש:
1. לסכם את הדיאלוג הקצר בין שני האנשים
2. לציין את הנושא העיקרי של הדיאלוג
3. להסביר את הקשר בין שתי ההודעות

יש לפרמט את הסיכום כך:

### סיכום דיאלוג קצר

**ההודעות:**
{formatted_messages}

**נושא הדיאלוג:**
[כאן יש לציין את הנושא העיקרי של הדיאלוג]

**ניתוח:**
[כאן יש לנתח את הקשר בין ההודעות והמשמעות של השיחה]

SUMMARY:
"""

    def _standard_summary_flow(self, messages, formatted_messages, target_language):
        """
        Standard summary generation flow as a fall-back option
        
        Args:
            messages (List[Dict[str, Any]]): List of messages
            formatted_messages (str): Pre-formatted messages
            target_language (str): Target language
            
        Returns:
            str: Generated summary
        """
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
            
            # Remove empty sections from the summary
            summary = self._remove_empty_sections(summary)
            
            self.logger.info("Summary generated successfully")
            return summary
            
        except openai.APIError as e:
            error_msg = f"OpenAI API error: {str(e)}"
            self.logger.error(error_msg)
            # Add request details to help diagnose the issue
            self.logger.error(f"Request details: model={self.model}, max_tokens={self.max_tokens}")
            
            # Create a basic fallback summary since we're already in a fallback method
            self.logger.info("Creating basic fallback summary due to API error")
            msg_texts = [f"{msg.get('senderName', 'Unknown')}: {msg.get('textMessage', '')}" 
                        for msg in messages if 'textMessage' in msg]
            return f"### סיכום בסיסי (בעקבות שגיאת API)\n\n" + "\n".join(msg_texts)
            
        except openai.RateLimitError as e:
            error_msg = f"OpenAI rate limit exceeded: {str(e)}"
            self.logger.error(error_msg)
            
            # Create a basic fallback summary
            self.logger.info("Creating basic fallback summary due to rate limit")
            msg_texts = [f"{msg.get('senderName', 'Unknown')}: {msg.get('textMessage', '')}" 
                        for msg in messages if 'textMessage' in msg]
            return f"### סיכום בסיסי (בעקבות הגבלת קצב API)\n\n" + "\n".join(msg_texts)

        except openai.APIConnectionError as e:
            error_msg = f"Failed to connect to OpenAI API: {str(e)}"
            self.logger.error(error_msg)
            
            # Create a basic fallback summary
            self.logger.info("Creating basic fallback summary due to connection error")
            msg_texts = [f"{msg.get('senderName', 'Unknown')}: {msg.get('textMessage', '')}" 
                        for msg in messages if 'textMessage' in msg]
            return f"### סיכום בסיסי (בעקבות שגיאת חיבור)\n\n" + "\n".join(msg_texts)

        except openai.InvalidRequestError as e:
            error_msg = f"Invalid request to OpenAI API: {str(e)}"
            self.logger.error(error_msg)
            # Log additional details about the request
            self.logger.error(f"Request details: model={self.model}, prompt_length={len(prompt)}")
            
            # Create a basic fallback summary
            self.logger.info("Creating basic fallback summary due to invalid request")
            msg_texts = [f"{msg.get('senderName', 'Unknown')}: {msg.get('textMessage', '')}" 
                        for msg in messages if 'textMessage' in msg]
            return f"### סיכום בסיסי (בעקבות בקשה לא תקינה)\n\n" + "\n".join(msg_texts)
            
        except Exception as e:
            self.logger.error(f"Error in standard summary flow: {str(e)}")
            # Create a very simple fallback summary
            self.logger.info("Creating basic fallback summary due to unexpected error")
            msg_texts = [f"{msg.get('senderName', 'Unknown')}: {msg.get('textMessage', '')}" 
                        for msg in messages if 'textMessage' in msg]
            return f"### סיכום בסיסי\n\n" + "\n".join(msg_texts)
    
    def _remove_empty_sections(self, summary: str) -> str:
        """
        Remove empty sections from the summary
        
        This function looks for sections that only contain a headline followed by:
        - No content
        - Empty bullet points
        - Statements indicating there's nothing to report like "No [items] found" or "None"
        
        Args:
            summary (str): The generated summary
            
        Returns:
            str: The summary with empty sections removed
        """
        self.logger.info("Removing empty sections from summary")
        
        # Split the summary into lines
        lines = summary.split('\n')
        
        # Process the lines
        result_lines = []
        section_start_index = -1
        current_section_has_content = False
        
        for i, line in enumerate(lines):
            # Check if this line is a section header (starts with ### or ####)
            is_section_header = line.strip().startswith('###')
            
            # If we found a new section header
            if is_section_header:
                # If we were processing a previous section
                if section_start_index >= 0:
                    # If the previous section had content, add it to result
                    if current_section_has_content:
                        result_lines.extend(lines[section_start_index:i])
                    # Otherwise, log that we're skipping an empty section
                    else:
                        skipped_header = lines[section_start_index].strip()
                        self.logger.info(f"Skipping empty section: {skipped_header}")
                
                # Start tracking the new section
                section_start_index = i
                current_section_has_content = False
            
            # Check if the current line contains actual content
            elif line.strip() and not line.strip().startswith('-'):
                current_section_has_content = True
            
            # Check if the line is a bullet point with content
            elif line.strip().startswith('-'):
                # Check if the bullet point has content beyond standard "none" indicators
                bullet_content = line.strip()[1:].strip()
                empty_indicators = [
                    "none", "no items", "no updates", "not available", "לא זמין", 
                    "אין", "לא נמצאו", "לא קיימים", "אין מידע", "not found", 
                    "אין עדכונים", "לא הוצגו", "לא דווחו", "לא התקבלו"
                ]
                
                if bullet_content and not any(indicator in bullet_content.lower() for indicator in empty_indicators):
                    current_section_has_content = True
        
        # Don't forget to process the last section
        if section_start_index >= 0:
            if current_section_has_content:
                result_lines.extend(lines[section_start_index:])
            else:
                skipped_header = lines[section_start_index].strip()
                self.logger.info(f"Skipping empty section: {skipped_header}")
        
        # Join the result lines back into a string
        processed_summary = '\n'.join(result_lines)
        
        # Add an info log about how many lines were removed
        removed_lines = len(lines) - len(result_lines)
        self.logger.info(f"Removed {removed_lines} lines from summary (empty sections)")
        
        return processed_summary 