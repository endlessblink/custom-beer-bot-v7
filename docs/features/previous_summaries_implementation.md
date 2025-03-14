# מימוש פיצ'ר "צפייה בסיכומים קודמים"

מסמך זה מתאר את הפתרון המוצע למימוש פיצ'ר "צפייה בסיכומים קודמים" בבוט סיכום הוואטסאפ.

## תיאור הפיצ'ר

הפיצ'ר יאפשר למשתמשים לצפות בסיכומים שנוצרו בעבר, כאשר לכל סיכום יוצג תיאור קצר שיעזור למשתמש לזהות את הסיכום המבוקש. המשתמש יוכל לבחור את הסיכום שמעניין אותו מרשימה, ולצפות בסיכום המלא.

## דרישות

1. שמירת סיכומים שנוצרו במסד הנתונים (Supabase)
2. יצירת תיאור קצר לכל סיכום
3. הצגת רשימת סיכומים קודמים עם התיאורים הקצרים
4. טעינת הסיכום המלא לאחר בחירת המשתמש

## מבנה נתונים

### טבלת Summaries

יש להוסיף/לעדכן את טבלת הסיכומים בסופבייס:

```sql
CREATE TABLE summaries (
    id SERIAL PRIMARY KEY,
    group_id VARCHAR(255) NOT NULL,
    group_name VARCHAR(255) NOT NULL,
    summary_text TEXT NOT NULL,
    short_description TEXT NOT NULL,
    message_count INTEGER,
    time_period TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- אינדקסים שמומלץ ליצור
CREATE INDEX summaries_group_id_idx ON summaries(group_id);
CREATE INDEX summaries_created_at_idx ON summaries(created_at);
```

## תהליך המימוש

### 1. יצירת תיאור קצר מסיכום

אחרי יצירת הסיכום, יש להשתמש ב-OpenAI כדי לחלץ תיאור קצר:

```python
def generate_short_description(full_summary, max_tokens=100):
    """יצירת תיאור קצר מהסיכום המלא באמצעות OpenAI."""
    from llm.openai_client import OpenAIClient
    
    openai_client = OpenAIClient()
    
    prompt = f"""
    לפניך סיכום של שיחת וואטסאפ. אנא צור 2-3 משפטים קצרים או רשימת מושגים מרכזיים 
    שמתארים את הנושאים העיקריים בסיכום. התוצאה צריכה להיות קצרה וממוקדת.
    
    הסיכום:
    {full_summary}
    
    תיאור קצר:
    """
    
    short_description = openai_client.generate_text(
        prompt=prompt,
        max_tokens=max_tokens
    )
    
    return short_description.strip()
```

### 2. שמירת הסיכום בסופבייס

יש לעדכן את הפונקציה שמטפלת בשמירת סיכומים כך שתשמור גם את התיאור הקצר:

```python
def save_summary_to_db(group_id, group_name, summary_text, message_count=0, time_period=""):
    """שמירת סיכום במסד הנתונים כולל תיאור קצר."""
    from db.supabase_client import SupabaseClient
    
    # בדיקה אם יש חיבור למסד נתונים
    try:
        supabase_client = SupabaseClient()
    except Exception as e:
        logging.error(f"Failed to connect to database: {e}")
        return False
    
    # יצירת תיאור קצר
    short_description = generate_short_description(summary_text)
    
    # הכנת הנתונים לשמירה
    summary_data = {
        "group_id": group_id,
        "group_name": group_name,
        "summary_text": summary_text,
        "short_description": short_description,
        "message_count": message_count,
        "time_period": time_period,
        "created_at": datetime.now().isoformat()
    }
    
    try:
        # שמירת הנתונים בסופבייס
        result = supabase_client.client.table("summaries").insert(summary_data).execute()
        
        # בדיקה אם השמירה הצליחה
        if len(result.data) > 0:
            logging.info(f"Summary saved to database with ID: {result.data[0]['id']}")
            return True
        else:
            logging.error("Failed to save summary to database")
            return False
    except Exception as e:
        logging.error(f"Error saving summary to database: {e}")
        return False
```

### 3. שליפת רשימת סיכומים קודמים

```python
def get_recent_summaries(limit=10):
    """שליפת הסיכומים האחרונים עם תיאור קצר."""
    from db.supabase_client import SupabaseClient
    
    try:
        supabase_client = SupabaseClient()
        
        # שליפת הנתונים מסופבייס
        result = supabase_client.client.table("summaries") \
            .select("id, group_name, short_description, created_at") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        
        if len(result.data) > 0:
            return result.data
        else:
            return []
    except Exception as e:
        logging.error(f"Error fetching summaries: {e}")
        return []
```

### 4. שליפת סיכום ספציפי

```python
def get_summary_by_id(summary_id):
    """שליפת סיכום מלא לפי מזהה."""
    from db.supabase_client import SupabaseClient
    
    try:
        supabase_client = SupabaseClient()
        
        # שליפת הסיכום מסופבייס
        result = supabase_client.client.table("summaries") \
            .select("*") \
            .eq("id", summary_id) \
            .execute()
        
        if len(result.data) > 0:
            return result.data[0]
        else:
            return None
    except Exception as e:
        logging.error(f"Error fetching summary with ID {summary_id}: {e}")
        return None
```

### 5. עדכון פונקציית התפריט לצפייה בסיכומים קודמים

```python
def view_previous_summaries():
    """תפריט לצפייה בסיכומים קודמים."""
    from utils.menu.core_menu import clear_screen, print_header, show_menu, display_error_and_continue
    import datetime

    clear_screen()
    print_header("צפייה בסיכומים קודמים")
    
    # בדיקה אם יש חיבור למסד נתונים
    try:
        from db.supabase_client import SupabaseClient
        supabase_client = SupabaseClient()
    except Exception as e:
        display_error_and_continue(
            "לא ניתן להשתמש בפיצ'ר זה ללא חיבור למסד נתונים.\n"
            f"שגיאה: {e}"
        )
        return
    
    # שליפת הסיכומים האחרונים
    summaries = get_recent_summaries(10)
    
    if not summaries:
        display_error_and_continue("לא נמצאו סיכומים קודמים במסד הנתונים.")
        return
    
    # יצירת אפשרויות תפריט מהסיכומים
    options = []
    for i, summary in enumerate(summaries, 1):
        # המרת התאריך לפורמט קריא
        created_date = datetime.datetime.fromisoformat(summary["created_at"].replace("Z", "+00:00"))
        formatted_date = created_date.strftime("%d/%m/%Y %H:%M")
        
        # יצירת טקסט האפשרות
        description = summary["short_description"]
        if len(description) > 50:
            description = description[:47] + "..."
        
        option_text = f"{formatted_date} | {summary['group_name']} | {description}"
        options.append({"key": str(i), "text": option_text})
    
    # הוספת אפשרות חזרה לתפריט הראשי
    options.append({"key": "b", "text": "חזרה לתפריט הראשי"})
    
    # הצגת התפריט וקבלת בחירת המשתמש
    choice = show_menu("בחר סיכום לצפייה:", options)
    
    if choice == "b":
        return
    
    try:
        # המרת הבחירה למספר ושליפת ה-ID של הסיכום
        summary_index = int(choice) - 1
        summary_id = summaries[summary_index]["id"]
        
        # שליפת הסיכום המלא
        full_summary = get_summary_by_id(summary_id)
        
        if not full_summary:
            display_error_and_continue("לא ניתן לטעון את הסיכום המבוקש.")
            return
        
        # הצגת הסיכום המלא
        clear_screen()
        print_header(f"סיכום: {full_summary['group_name']}")
        
        print(f"תאריך: {datetime.datetime.fromisoformat(full_summary['created_at'].replace('Z', '+00:00')).strftime('%d/%m/%Y %H:%M')}")
        if full_summary.get("time_period"):
            print(f"תקופה: {full_summary['time_period']}")
        if full_summary.get("message_count"):
            print(f"מספר הודעות: {full_summary['message_count']}")
        
        print("\n" + "=" * 80 + "\n")
        print(full_summary["summary_text"])
        print("\n" + "=" * 80)
        
        input("\nלחץ Enter כדי לחזור...")
        
    except (ValueError, IndexError):
        display_error_and_continue("בחירה לא תקינה.")
        return
```

## שילוב הפיצ'ר בתפריט הראשי

יש לעדכן את התפריט הראשי כך שהאפשרות "צפייה בסיכומים קודמים" תפנה לפונקציה החדשה:

```python
def run_main_menu():
    # ... קוד קיים ...
    
    if choice == "2":  # View Previous Summaries
        view_previous_summaries()
    
    # ... המשך הקוד הקיים ...
```

## טיפול במצב ללא מסד נתונים

כאשר אין חיבור למסד נתונים, הפיצ'ר יציג הודעה מתאימה למשתמש:

```
לא ניתן להשתמש בפיצ'ר זה ללא חיבור למסד נתונים.
שגיאה: [פרטי השגיאה]
```

## הערכת זמן לפיתוח

* הגדרת שינויים במבנה הטבלה: 0.5 שעה
* פיתוח פונקציית יצירת תיאור קצר: 1-2 שעות
* פיתוח פונקציות שמירה ושליפה מהדאטאבייס: 1-2 שעות
* פיתוח ממשק המשתמש (תפריט): 2-3 שעות
* בדיקות ותיקון באגים: 1 שעה

**סה"כ: 5.5-8.5 שעות עבודה**

## יתרונות הפתרון

1. **ניצול תשתית קיימת** - משתמש במסד הנתונים הקיים
2. **חוויית משתמש טובה** - תיאורים קצרים מאפשרים למשתמש לבחור בקלות את הסיכום המבוקש
3. **ביצועים טובים** - העומס על מסד הנתונים מינימלי
4. **שקיפות** - המשתמש מקבל משוב ברור כשהפיצ'ר לא זמין 