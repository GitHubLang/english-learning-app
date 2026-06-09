"""
快速查看课本信息和TEM-8教材
"""
import mysql.connector
DB = dict(host='192.168.71.189', user='root', password='notes123', database='english_db')
conn = mysql.connector.connect(**DB)
cur = conn.cursor(dictionary=True)

# 所有课本
cur.execute("SELECT * FROM word_textbooks")
books = cur.fetchall()
print("=== 所有课本 ===")
for b in books:
    cur.execute("SELECT COUNT(*) as cnt FROM words WHERE textbook_id = %s", (b['id'],))
    cnt = cur.fetchone()['cnt']
    print(f"  ID={b['id']:2d}  |  {b['title'][:30]:30s}  |  单词数: {cnt}")

# 找含"八级"或"专八"或"TEM8"的
print("\n=== 含专八关键词的课本 ===")
for b in books:
    title = (b.get('title') or '') + (b.get('book_name') or '') + (b.get('alias') or '')
    if '八' in title or '专八' in title or 'TEM8' in title.upper() or '专业' in title:
        print(f"  ID={b['id']:2d}  |  title={b['title']}  |  book_name={b['book_name']}  |  alias={b['alias']}")

# 查询 distinct words count for each textbook
print("\n=== 各课本去重单词数 ===")
for b in books:
    cur.execute("SELECT COUNT(DISTINCT word) FROM words WHERE textbook_id = %s", (b['id'],))
    distinct = cur.fetchone()['COUNT(DISTINCT word)']
    print(f"  ID={b['id']:2d}  |  {b['title'][:30]:30s}  |  去重: {distinct}")

cur.close()
conn.close()
