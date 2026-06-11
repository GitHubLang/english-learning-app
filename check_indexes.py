import mysql.connector
from mysql.connector import pooling

pool = pooling.MySQLConnectionPool(
    pool_name='test_pool', pool_size=1,
    host='192.168.71.189', user='root', password='notes123', database='english_db'
)
db = pool.get_connection()
cursor = db.cursor()

cursor.execute("SHOW TABLES")
print('Tables:')
for row in cursor.fetchall():
    print(f'  {row[0]}')

cursor.execute("SHOW INDEX FROM words")
print('\nIndexes on words:')
for row in cursor.fetchall():
    print(f'  {row[2]} on {row[4]} ({row[1]})')

cursor.execute("SHOW INDEX FROM word_play_records")
print('\nIndexes on word_play_records:')
for row in cursor.fetchall():
    print(f'  {row[2]} on {row[4]} ({row[1]})')

cursor.execute("SHOW INDEX FROM word_textbooks")
print('\nIndexes on word_textbooks:')
for row in cursor.fetchall():
    print(f'  {row[2]} on {row[4]} ({row[1]})')

cursor.close()
db.close()
