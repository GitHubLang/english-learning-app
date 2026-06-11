import mysql.connector
from mysql.connector import pooling
import hashlib
import os
import json

BASE_DIR = 'D:\\myProject\\english-learning-app'
CACHE_DIR = os.path.join(BASE_DIR, 'cached_tts')
VOICE_ZH = 'zh-CN-XiaoxiaoNeural'

def text_cached(text, voice):
    key = hashlib.md5(f"{text}:{voice}".encode()).hexdigest()
    subdir = key[:2]
    return os.path.exists(os.path.join(CACHE_DIR, subdir, f"{key}.mp3"))

def _extract_zh_from_word_json(rows):
    meanings = set()
    sentences = set()
    for (wj,) in rows:
        try:
            data = json.loads(wj)
            content = data.get('content', {})
            wc = content.get('word', {}).get('content', {})
            trans = wc.get('trans', [])
            for t in trans:
                cn = (t.get('tranCn') or '').strip()
                pos = (t.get('pos') or '').strip()
                if cn:
                    text = f"{pos} {cn}".strip() if pos else cn
                    meanings.add(text)
            sdata = wc.get('sentence', {}).get('sentences', [])
            for s in sdata:
                scn = (s.get('sCn') or '').strip()
                if scn and len(scn) > 1:
                    sentences.add(scn)
        except:
            pass
    return meanings, sentences

pool = pooling.MySQLConnectionPool(
    pool_name='test_pool', pool_size=1,
    host='192.168.71.189', user='root', password='notes123', database='english_db'
)
db = pool.get_connection()
cursor = db.cursor()

# Count word_json entries
cursor.execute("SELECT COUNT(*) FROM words WHERE word_json IS NOT NULL AND word_json != ''")
total = cursor.fetchone()[0]
print(f"Total words with word_json: {total}")

# Let's do a sample to estimate
cursor.execute("""
    SELECT word_json FROM words 
    WHERE word_json IS NOT NULL AND word_json != '' 
    LIMIT 5000
""")
rows = cursor.fetchall()
cursor.close()
db.close()

meanings, sentences = _extract_zh_from_word_json(rows)

total_meaning_texts = len(meanings)
total_sentence_texts = len(sentences)
print(f"\nFrom 5000 samples:")
print(f"  Unique meaning texts: {total_meaning_texts}")
print(f"  Unique sentence texts: {total_sentence_texts}")

# Check cache status
uncached_meanings = [t for t in meanings if not text_cached(t, VOICE_ZH)]
uncached_sentences = [t for t in sentences if not text_cached(t, VOICE_ZH)]

print(f"\nZH cache status (from 5000 samples):")
print(f"  Meanings: {total_meaning_texts - len(uncached_meanings)}/{total_meaning_texts} cached → {len(uncached_meanings)} uncached")
print(f"  Sentences: {total_sentence_texts - len(uncached_sentences)}/{total_sentence_texts} cached → {len(uncached_sentences)} uncached")

print(f"\nSample of uncached meaning texts:")
for t in list(uncached_meanings)[:10]:
    print(f"  [{len(t)} chars] {t}")

print(f"\nSample of cached meaning texts:")
cached = [t for t in meanings if text_cached(t, VOICE_ZH)]
for t in list(cached)[:5]:
    print(f"  [{len(t)} chars] {t}")
