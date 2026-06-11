import mysql.connector
from mysql.connector import pooling
import time

pool = pooling.MySQLConnectionPool(
    pool_name='test_pool', pool_size=1,
    host='192.168.71.189', user='root', password='notes123', database='english_db'
)

# Test 1: Basic GET word by ID (simulates word detail)
db = pool.get_connection()
cursor = db.cursor(dictionary=True)

word_id = 1
t0 = time.time()
cursor.execute("SELECT id, textbook_id, book_name, word, word_json FROM words WHERE id = %s", (word_id,))
word_row = cursor.fetchone()
t1 = time.time()
print(f'GET word by ID ({word_id}): {t1-t0:.3f}s')

# Test 2: Simulate random word query for a small textbook
textbook_id = 1  # ~1162 words
t0 = time.time()
cursor.execute("""
    SELECT w.id, COALESCE(wpr.play_count, 0) as play_count
    FROM words w
    LEFT JOIN word_play_records wpr ON w.id = wpr.word_id 
        AND wpr.user_id = %s AND wpr.textbook_id = %s
    WHERE w.textbook_id = %s
""", (1, textbook_id, textbook_id))
records = cursor.fetchall()
t1 = time.time()
print(f'Random word query (textbook {textbook_id}, {len(records)} words): {t1-t0:.3f}s')

# Test 3: Simulate random word query for BIG textbook
textbook_id = 82  # ~52767 words
t0 = time.time()
cursor.execute("""
    SELECT w.id, COALESCE(wpr.play_count, 0) as play_count
    FROM words w
    LEFT JOIN word_play_records wpr ON w.id = wpr.word_id 
        AND wpr.user_id = %s AND wpr.textbook_id = %s
    WHERE w.textbook_id = %s
""", (1, textbook_id, textbook_id))
records = cursor.fetchall()
t1 = time.time()
print(f'Random word query (textbook {textbook_id}, {len(records)} words): {t1-t0:.3f}s')
print(f'  Min play_count: {min(r["play_count"] for r in records)}')

# Test 4: Search LIKE prefix
t0 = time.time()
cursor.execute("SELECT COUNT(*) FROM words WHERE word LIKE 'ab%'")
cnt = cursor.fetchone()['COUNT(*)']
t1 = time.time()
print(f'\nSearch LIKE "ab%": {cnt} results, {t1-t0:.3f}s')

t0 = time.time()
cursor.execute("""
    SELECT w.id, w.textbook_id, w.book_name, w.word, length(w.word_json) as json_size
    FROM words w
    LEFT JOIN word_textbooks t ON w.textbook_id = t.id
    WHERE w.word LIKE 'ab%'
    GROUP BY w.textbook_id, w.word
    ORDER BY CASE WHEN w.word = 'ab' THEN 0 ELSE 1 END, LENGTH(w.word)
    LIMIT 50
""")
results = cursor.fetchall()
t1 = time.time()
print(f'Search LIKE "ab%" with GROUP BY: {len(results)} results, {t1-t0:.3f}s')

# Test 5: Search LIKE prefix for a more specific word
t0 = time.time()
cursor.execute("""
    SELECT w.id, w.textbook_id, w.book_name, w.word, length(w.word_json) as json_size
    FROM words w
    LEFT JOIN word_textbooks t ON w.textbook_id = t.id
    WHERE w.word LIKE 'abandon%'
    GROUP BY w.textbook_id, w.word
    ORDER BY CASE WHEN w.word = 'abandon' THEN 0 ELSE 1 END, LENGTH(w.word)
    LIMIT 50
""")
results = cursor.fetchall()
t1 = time.time()
print(f'Search LIKE "abandon%": {len(results)} results, {t1-t0:.3f}s')

cursor.close()
db.close()
