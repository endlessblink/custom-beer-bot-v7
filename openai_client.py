from typing import List, Dict, Any
from datetime import datetime
import logging
import os

class OpenAIClient:
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
                # Try different approaches to sort by timestamp
                try:
                    # First attempt: Try sorting directly if timestamps are all numeric
                    messages_with_timestamp.sort(key=lambda msg: int(msg['timestamp']) 
                                                if isinstance(msg['timestamp'], (int, str)) and str(msg['timestamp']).isdigit() 
                                                else 0)
                    messages = messages_with_timestamp
                    logging.info("Sorted messages using numeric timestamp values")
                except (ValueError, TypeError) as e:
                    logging.warning(f"Error in first sort attempt: {str(e)}")
                    
                    # Second attempt: Use a more flexible sorting approach
                    def get_timestamp_value(msg):
                        ts = msg.get('timestamp')
                        if isinstance(ts, int):
                            return ts
                        elif isinstance(ts, str):
                            if ts.isdigit():
                                return int(ts)
                            else:
                                # Try to parse formatted date strings
                                try:
                                    # Try common date formats
                                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y %H:%M:%S']:
                                        try:
                                            dt = datetime.strptime(ts, fmt)
                                            return int(dt.timestamp())
                                        except ValueError:
                                            continue
                                except Exception:
                                    pass
                            return 0
                        return 0
                    
                    try:
                        messages_with_timestamp.sort(key=get_timestamp_value)
                        messages = messages_with_timestamp
                        logging.info("Sorted messages using flexible timestamp parsing")
                    except Exception as sort_error:
                        logging.warning(f"Failed to sort messages by timestamp: {str(sort_error)}")
                        # Fall back to the original message order
                        logging.info("Using original message order")
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
                time_str = "Unknown time"
                
                # Use normalized timestamp if available
                if 'timestamp_normalized' in msg:
                    time_str = msg['timestamp_normalized']
                else:
                    # Fall back to original timestamp handling
                    timestamp = msg.get('timestamp')
                    
                    if timestamp is not None:
                        try:
                            if isinstance(timestamp, int):
                                time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                            elif isinstance(timestamp, str):
                                # If it's a numeric string, convert to int first
                                if timestamp.isdigit():
                                    time_str = datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
                                else:
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
        
        return "\n".join(formatted_messages) 

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
        
        # Diagnostic logging
        message_types = {}
        for msg in messages:
            msg_type = msg.get('typeMessage', 'unknown')
            message_types[msg_type] = message_types.get(msg_type, 0) + 1
        
        logging.info(f"Message types in input: {message_types}")
        
        # Normalize timestamps before formatting messages
        # This helps prevent conversion warnings during formatting
        for msg in messages:
            if 'timestamp' in msg and msg['timestamp'] is not None:
                # If timestamp is already a string in date format, leave it alone
                if isinstance(msg['timestamp'], str) and not msg['timestamp'].isdigit():
                    # It's already a formatted date string, so we'll keep it as is
                    continue
                
                try:
                    # Convert to integer timestamp if possible
                    ts_value = int(msg['timestamp']) if isinstance(msg['timestamp'], str) else msg['timestamp']
                    
                    # Store as string in standard format to avoid repeated conversions
                    msg['timestamp_normalized'] = datetime.fromtimestamp(ts_value).strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError, OverflowError) as e:
                    # If conversion fails, store original
                    msg['timestamp_normalized'] = str(msg['timestamp'])
                    logging.debug(f"Could not normalize timestamp {msg['timestamp']}: {str(e)}")
        
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
1. **שים לב: דרוש סיכום עדכני של הדיונים!** 
   - התייחס רק להודעות בשיחה המצורפת
   - אל תסתמך על סיכומים קודמים שיתכן ויצרת
   - אם נושא מסוים הופיע בסיכומים קודמים אך לא בהודעות הנוכחיות, אל תכלול אותו
   - הקפד לכלול נושאים חדשים שעלו בדיונים האחרונים

2. עליך לחפש ולהתייחס באופן אקטיבי לכל התוכן בהודעות, גם אם מדובר בפרטים קטנים
3. אל תחזיר תבנית ריקה עם "לא דווח" בכל הסעיפים - אם יש תוכן כלשהו, צרף אותו תחת הקטגוריה המתאימה
4. אם יש תוכן שאינו מתאים לקטגוריות הקיימות, הוסף הערה בסוף הסיכום
5. אם סעיף מסוים אכן ריק, רשום "לא דווח" רק עבורו, ולא עבור כל הסעיפים
6. אם מוזכר תוכן או קישור כלשהו, כלול אותו בסיכום
7. חשוב מאוד: עליך לסכם את כל המידע המהותי, גם אם מופיע רק פעם אחת בשיחה
8. אם יש תכנים דומים שחוזרים על עצמם, אחד אותם תחת סעיף אחד

9. **התעדכנות חשובה:** בהודעות אלו מופיע מידע חדש ועדכני שיתכן לא הופיע בסיכומים קודמים.
   עליך לוודא שהסיכום משקף את המידע העדכני ביותר.

{prompt_template}

כעת נמצאות בפניך ההודעות לסיכום. יש בסך הכל כ-[מספר] הודעות, חלקן אינפורמטיביות וחלקן פחות.
בכל מקרה, עליך לסרוק את כל ההודעות ולסכם את כל המידע המהותי שנמצא בהן.

TIMESTAMP: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

CONVERSATION:
{formatted_messages}

SUMMARY:
"""

        # החלף את המילה [מספר] במספר המשוער של ההודעות
        message_count = formatted_messages.count('\n') + 1  # הערכה גסה של מספר ההודעות
        better_instruction = better_instruction.replace('[מספר]', str(message_count))
        
        return better_instruction 