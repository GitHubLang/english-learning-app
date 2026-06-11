import mysql.connector
from mysql.connector import pooling

pool = pooling.MySQLConnectionPool(
    pool_name='test_pool', pool_size=1,
    host='192.168.71.189', user='root', password='notes123', database='english_db'
)
db = pool.get_connection()
cursor = db.cursor()

cursor.execute('SELECT COUNT(*) FROM words')
print(f'Total words: {cursor.fetchone()[0]}')

cursor.execute('SELECT AVG(LENGTH(word_json)), MAX(LENGTH(word_json)) FROM words')
avg_len, max_len = cursor.fetchone()
print(f'Avg word_json length: {avg_len:.0f} bytes = {avg_len/1024:.1f} KB')
print(f'Max word_json length: {max_len} bytes = {max_len/1024:.1f} KB')

cursor.execute('SELECT word, LENGTH(word_json) FROM words ORDER BY LENGTH(word_json) DESC LIMIT 5')
print('\nLargest word_json entries:')
for word, size in cursor.fetchall():
    print(f'  {word}: {size/1024:.1f} KB')

# Check number of textbooks
cursor.execute('SELECT COUNT(*) FROM word_textbooks')
print(f'\nTotal textbooks: {cursor.fetchone()[0]}')

cursor.execute('SELECT id, title, word_count FROM word_textbooks LIMIT 10')
print('\nTextbooks:')
for row in cursor.fetchall():
    print(f'  id={row[0]}, title={row[1]}, word_count={row[2]}')

# Check word count per textbook
cursor.execute('SELECT textbook_id, COUNT(*) FROM words GROUP BY textbook_id ORDER BY textbook_id')
print('\nWords per textbook:')
for row in cursor.fetchall():
    print(f'  textbook_id={row[0]}: {row[1]} words')

cursor.close()
db.close()
