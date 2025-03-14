# תפריט בסיסי - מודול קריטי

מודול זה מכיל את הפונקציונליות הבסיסית של התפריט האינטראקטיבי של בוט סיכום הוואטסאפ.

## חשיבות

**זהו מודול קריטי שחייב להישמר ולהישאר תקין בכל הגרסאות של הפרויקט.**

התפריט האינטראקטיבי הוא רכיב מרכזי בחוויית המשתמש של המערכת, והוא חייב לפעול תמיד, גם אם יש בעיות בחלקים אחרים של המערכת.

## עקרונות התכנון

1. **עצמאות**: המודול תוכנן להיות עצמאי ככל האפשר, כך שהוא לא ייפגע משינויים בחלקים אחרים של הקוד.

2. **חוסן**: המודול מסוגל להתמודד עם מצבים שבהם רכיבים אחרים של המערכת אינם זמינים.

3. **גמישות**: המודול מאפשר להציג או להסתיר אפשרויות בתפריט בהתאם לזמינות של רכיבים שונים.

4. **פשטות**: הממשק פשוט ואינטואיטיבי, מה שמקל על תחזוקה ושדרוגים.

## פונקציות מרכזיות

- `clear_screen()`: מנקה את המסך
- `print_header()`: מדפיס את הכותרת של היישום
- `show_menu()`: מציג תפריט ומקבל בחירה מהמשתמש
- `display_error_and_continue()`: מציג הודעת שגיאה וממתין ללחיצה על Enter
- `confirm_action()`: מבקש אישור מהמשתמש

## שימוש במודול

יש להשתמש במודול זה בכל מקום שבו נדרש תפריט אינטראקטיבי ביישום. אין ליצור יישומים מקבילים או לעקוף את הפונקציונליות המוגדרת כאן.

```python
from utils.menu.core_menu import show_menu, display_error_and_continue

# הגדרת אפשרויות התפריט
options = [
    {'key': '1', 'text': 'אפשרות ראשונה'},
    {'key': '2', 'text': 'אפשרות שנייה'},
    {'key': '3', 'text': 'יציאה'}
]

# הצגת התפריט וקבלת בחירת המשתמש
choice = show_menu("תפריט ראשי", options)
```

## אזהרה!

**אין לשנות את הקוד במודול זה ללא בדיקות יסודיות!**

כל שינוי במודול זה עלול להשפיע על פונקציונליות בסיסית של היישום. יש לתעד היטב כל שינוי ולוודא שהוא עובר בדיקות מקיפות לפני שילובו בקוד הראשי. 