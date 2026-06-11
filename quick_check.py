import mysql.connector
import hashlib
import os
import json
import time

BASE_DIR = 'D:\\myProject\\english-learning-app'
CACHE_DIR = os.path.join(BASE_DIR, 'cached_tts')
VOICE_ZH = 'zh-CN-XiaoxiaoNeural'

def text_cached(text, voice=VOICE_ZH):
    key = hashlib.md5(f"{text}:{voice}".encode()).hexdigest()
    subdir = key[:2]
    return os.path.exists(os.path.join(CACHE_DIR, subdir, f"{key}.mp3"))

# Check: all books with counts
conn = mysql.connector.connect(host='192.168.71.189', user='root', password='notes123', database='english_db')
cur = conn.cursor()
cur.execute("""
    SELECT w.textbook_id, t.title, COUNT(*) as cnt
    FROM words w
    JOIN word_textbooks t ON w.textbook_id = t.id
    GROUP BY w.textbook_id, t.title
    ORDER BY cnt DESC
""")
print("Textbooks by word count:")
for row in cur.fetchall():
    print(f"  #{row[0]} {row[1]}: {row[2]} words")

# Check user's recent textbooks
cur.execute("""
    SELECT textbook_id, COUNT(*) as play_count, MAX(updated_at) as last_played
    FROM word_play_records
    WHERE user_id = 1
    GROUP BY textbook_id
    ORDER BY last_played DESC
    LIMIT 5
""")
print("\nUser #1 most recent textbooks:")
for row in cur.fetchall():
    print(f"  textbook #{row[0]}: {row[1]} plays, last at {row[2]}")

cur.close()
conn.close()

print("\n== Quick check: how many ZH texts are actually uncached ==")
print("(sampling 50000 words, counting uncached ZH meaning texts)")
