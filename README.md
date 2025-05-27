# TelegramDownloader
Downloads from Telegram channels to PC. -Python -Telethon


Requirements:
telethon
python-dotenv




English:

First edit the 'Telegram Downloader By AniKofKatan.py' File. ( Notpad/Vscode )
Search for :
api_id = int(os.getenv('TELEGRAM_API_ID', '123123123'))
api_hash = os.getenv('TELEGRAM_API_HASH', '123123123')
-Edit the '123123123' to your actual Telegram API ID and HASH.
You can find them here : https://my.telegram.org

And then search for :
source_group = int(os.getenv('SOURCE_GROUP', '-100123123123'))
-Edit the 123123123 to your channel ID.
-Remember to keep the '-100' before the channel ID!

Then you run the file, and login again, and it will start downloading everything to a folder near the .py file.

Commands and adjustments:
'SS' = Skip this file

Edit current post:
A new file will be created in the same directory near the .py called 'download_progress.json'
Adjust "last_id": X - With the post number you before the one you want to start with.


A session file will be created once the login is successful with your credentials. DO NOT SHARE IT WITH ANYONE! This is your access to your account.


עברית:

חייב להוריד telethon וpython-dotenv


תחילה ערוך את הקובץ Telegram Downloader By AniKofKatan.py (באמצעות Notepad או VSCode).
חפש את השורות:

api_id = int(os.getenv('TELEGRAM_API_ID', '123123123'))
api_hash = os.getenv('TELEGRAM_API_HASH', '123123123')

ערוך את המספרים '123123123' והכנס את ה-API ID וה-API HASH שלך מטלגרם.
ניתן למצוא אותם כאן: https://my.telegram.org/

לאחר מכן חפש את השורה:

source_group = int(os.getenv('SOURCE_GROUP', '-100123123123'))

ערוך את המספר 123123123 והכנס את מזהה הערוץ שלך.
זכור להשאיר את '-100' לפני מזהה הערוץ!

לאחר מכן תריץ את הקובץ, תתחבר מחדש, והתוכנה תתחיל להוריד את הכל לתיקייה שנמצאת ליד קובץ ה-.py.

פקודות והתאמות:
SS = דלג על הקובץ הזה

עריכת הפוסט הנוכחי:
קובץ חדש ייווצר באותה תיקייה ליד קובץ ה-.py בשם download_progress.json
ערוך את השדה "last_id" והכנס בו את מספר הפוסט שלפני הפוסט שממנו אתה רוצה להתחיל.

קובץ session ייווצר לאחר התחברות מוצלחת עם הפרטים שלך.
אל תשתף אותו עם אף אחד! זהו הקובץ שמאפשר גישה לחשבון שלך.




