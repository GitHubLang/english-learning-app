"""
预检：统计需要缓存的单词数量
"""
import mysql.connector
import hashlib
import os

DB = dict(host='192.168.71.189', user='root', password='notes123', database='english_db')
CACHE_DIR = os.path.join(r'D:\myProject\english-learning-app', 'cached_tts')
VOICE_EN = 'en-US-JennyNeural'

def get_cache_path(text, voice):
    cache_key = hashlib.md5(f"{text}:{voice}".encode()).hexdigest()
    subdir = cache_key[:2]
    return os.path.join(CACHE_DIR, subdir, f"{cache_key}.mp3")

conn = mysql.connector.connect(**DB)
cur = conn.cursor()

cur.execute("SELECT DISTINCT LOWER(TRIM(word)) FROM words WHERE word IS NOT NULL AND TRIM(word) != '' ORDER BY word")
words = [r[0] for r in cur.fetchall()]
cur.close()
conn.close()

print(f"去重后单词数: {len(words)}")

# 检查已有缓存（旧格式 + 新格式）
cached = 0
old_cached = 0
for w in words:
    # 新子目录格式
    p = get_cache_path(w, VOICE_EN)
    if os.path.exists(p):
        cached += 1
    # 旧根目录格式
    old_key = hashlib.md5(f"{w}:{VOICE_EN}".encode()).hexdigest()
    old_p = os.path.join(CACHE_DIR, f"{old_key}.mp3")
    if os.path.exists(old_p):
        old_cached += 1

print(f"已缓存（新子目录）: {cached}")
print(f"已缓存（旧根目录）: {old_cached}")
print(f"待缓存: {len(words) - cached - old_cached}")
print(f"现有 cached_tts/ 根目录文件: {len([f for f in os.listdir(CACHE_DIR) if f.endswith('.mp3') and os.path.isfile(os.path.join(CACHE_DIR, f))]) if os.path.exists(CACHE_DIR) else 0}")
