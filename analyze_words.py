"""
快速分析：单词质量 & 缓存预估
"""
import mysql.connector
import hashlib, os, json, re

DB = dict(host='192.168.71.189', user='root', password='notes123', database='english_db')
CACHE_DIR = r'D:\myProject\english-learning-app\cached_tts'
VOICE_EN = 'en-US-JennyNeural'

def get_word_text(word_json_str):
    """从 word_json 提取单词头"""
    try:
        d = json.loads(word_json_str)
        return d.get('headWord', '').strip().lower()
    except:
        return ''

conn = mysql.connector.connect(**DB)
cur = conn.cursor()

# 获取所有单词（带 word_json）
cur.execute("SELECT word, word_json FROM words WHERE word IS NOT NULL AND TRIM(word) != ''")
all_rows = cur.fetchall()
cur.close()
conn.close()

print(f"总记录数: {len(all_rows)}")

# 分析
word_set = set()
invalid = 0
short_words = 0
long_words = 0
has_json = 0

for word, wj in all_rows:
    w = word.strip().lower()
    if not w or not re.match(r'^[a-z]', w):
        invalid += 1
        continue
    if len(w) <= 1:
        short_words += 1
        continue
    if len(w) > 30:
        long_words += 1
        continue
    word_set.add(w)
    if wj and len(wj) > 10:
        has_json += 1

print(f"有效去重单词: {len(word_set)}")
print(f"无效记录(非字母开头): {invalid}")
print(f"过短(≤1字符): {short_words}")
print(f"过长(>30字符): {long_words}")

# 已有缓存统计
old_root = [f for f in os.listdir(CACHE_DIR) if f.endswith('.mp3') and os.path.isfile(os.path.join(CACHE_DIR, f))]
new_subdirs = 0
for root, dirs, files in os.walk(CACHE_DIR):
    if root != CACHE_DIR:
        new_subdirs += len([f for f in files if f.endswith('.mp3')])

print(f"\n--- 缓存现状 ---")
print(f"缓存根目录旧文件: {len(old_root)}")
print(f"子目录缓存文件: {new_subdirs}")
print(f"合计: {len(old_root) + new_subdirs}")

# 预估需要新缓存的单词（排除已有）
existing = set()
old_root_existing = 0
for fname in old_root:
    key = fname.replace('.mp3', '')
    existing.add(key)
    old_root_existing += 1

# 渐进式缓存：只缓存真正会遇到的单词
print(f"\n--- 建议 ---")
print(f"去重后真正需要发音的单词约 {len(word_set)} 个")
print(f"其中 {len(existing)} 个已有缓存")
print(f"需要新增约 {len(word_set) - len(existing)} 个")
print(f"\n如按 0.5秒/个 估算，耗时约 {(len(word_set) - len(existing)) * 0.5 / 3600:.1f} 小时")
