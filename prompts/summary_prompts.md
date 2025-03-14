<div dir="rtl">

# פרומפטים לכתיבת סיכומים בבוט WhatsApp

מסמך זה מכיל את פורמט הסיכום המועדף לקבוצת Custom Beer Node העוסקת בפיתוחים של בינה מלאכותית גנרטיבית בקוד פתוח.

## פורמט הסיכום המועדף

```
צור סיכום מובנה של שיחות קבוצת Custom Beer Node בפורמט הבא:

## סיכום שיחות קבוצת Custom Beer Node
### תאריך: [תאריך] | תקופה: [טווח זמן הסיכום]

### 😂 בדיחת AI היום:
[בדיחה קצרה וקולעת הקשורה לבינה מלאכותית]

### 1. פרויקטים ופיתוחים שהוצגו
- [שם פרויקט/מודל] - [מפתח/ת] - [תיאור קצר ותכונות עיקריות]

### 2. תוצרים ודמואים שהוצגו
- [סוג תוצר] שיצר [משתמש] - [תיאור קצר] - [מאפיינים טכניים]
- [קישור לתמונות/וידאו אם זמין]

### 3. כלים וטכנולוגיות חדשים שנדונו
- [שם הכלי/טכנולוגיה] - [מפתח או חברה] - [שימושים עיקריים/יתרונות]

### 4. בעיות טכניות ופתרונות שהוצעו
- [בעיה] - [הצעות לפתרון] - [מציע הפתרון]

### 5. משאבים ומאמרים שהועברו
- [נושא] - [הקישור המלא לפרויקט/אתר/מאמר] - [שיתף: משתמש]

### 6. סטטוס פרויקטים מתמשכים
- [שם פרויקט] - [התקדמות] - [מפתח/ים]

### 7. שאלות פתוחות ותחומי עניין לעתיד
- [שאלה/נושא] - [הועלה על ידי: משתמש]

### 8. חידושים בתחום בינה מלאכותית גנרטיבית
- [חידוש] - [השלכות] - [מקור]

### 9. ווקפלואים (workflows) של ComfyUI שהועברו
- [תיאור הווקפלואו] - [יוצר] - [תוצאה] - [קישור אם קיים]

### 10. מושגים טכניים חדשים שנדונו
- [מושג] - [הסבר קצר] - [הקשר לפרויקטים בקבוצה]

הנחיות נוספות:
- הקפד לכלול את כל הקישורים (URLs) שהועברו בקבוצה, גם אם הם הוזכרו בהקשר אחר
- השתמש רק בסעיפים שיש בהם תוכן ממשי - אל תכתוב "לא דווח על..." או "אין מידע על..."
- אם אין תוכן לסעיף מסוים, השמט אותו לחלוטין מהסיכום
- הקפד על תמציתיות וברורות בכל נקודה
- אזכר שמות המשתתפים רק כאשר זה רלוונטי להקשר
- שמור על טון ענייני ומקצועי
- השתמש בשפה רהוטה, ברורה וללא שגיאות
```

## שילוב הפרומפט במערכת

הפרומפט משולב במערכת דרך משתנה הסביבה `SUMMARY_PROMPT` בקובץ `.env`.

המערכת קוראת את הפרומפט מקובץ ה-`.env` באמצעות הקוד הבא בקובץ `llm/openai_client.py`:

```python
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
        # Fallback prompt template if env variable not set
        prompt_template = """...default template..."""

    return f"""
הנך מתבקש לסכם את השיחה הבאה מקבוצת WhatsApp ב{target_language}.
{prompt_template}

CONVERSATION:
{formatted_messages}

SUMMARY:
""" 
```

## דוגמאות לבדיחות AI

הנה מספר דוגמאות לבדיחות AI שיכולות להתאים לתחילת הסיכום:

1. "למה מודל שפה גדול הפסיק לענות לשאלות? כי הוא הגיע למגבלת הטוקנים והלך לישון!"

2. "שני מודלי AI נכנסים לבר. האחד אומר לשני: 'הטמפרטורה שלי היום על 0.7' והשני עונה: 'מזל, אני על 0.1 וכל מה שאני אומר משעמם בצורה צפויה...'"

3. "איך אתה יודע שדיברת יותר מדי עם ChatGPT? כשאתה מסיים משפטים במציאות ומחפש את כפתור ה-Submit."

4. "שמעתם על הפרומפט אנג'יניר שניסה לאמן את הכלב שלו? הוא עדיין מנסח מחדש את הפקודה 'שב' כבר שבועיים..."

5. "למה מודל דיפוזיה תמיד מבולבל? כי יש לו יותר מדי רעש בראש."