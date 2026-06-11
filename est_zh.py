import mysql.connector
import hashlib
import os
import json
import time

BASE_DIR = 'D:\\myProject\\english-learning-app'
CACHE_DIR = os.path.join(BASE_DIR, 'cached_tts')
VOICE_ZH = 'zh-CN-XiaoxiaoNeural'

def text_cached(text, voice):
    key = hashlib.md5(f"{text}:{voice}".encode()).hexdigest()
    subdir = key[:2]
    return os.path.exists(os.path.join(CACHE_DIR, subdir, f"{key}.mp3"))

conn = mysql.connector.connect(host='192.168.71.189', user='root', password='notes123', database='english_db')
cur = conn.cursor()

# Quick estimate: process a batch
cur.execute("SELECT word_json FROM words WHERE word_json IS NOT NULL AND word_json != '' LIMIT 20000")
rows = cur.fetchall()
cur.close()
conn.close()

meaning_texts = set()
sentence_texts = set()

for (wj,) in rows:
    try:
        data = json.loads(wj)
        wc = data.get('content', {}).get('word', {}).get('content', {})
        for t in wc.get('trans', []):
            cn = (t.get('tranCn') or '').strip()
            pos = (t.get('pos') or '').strip()
            if cn:
                meaning_texts.add(f"{pos} {cn}".strip() if pos else cn)
        for s in wc.get('sentence', {}).get('sentences', []):
            scn = (s.get('sCn') or '').strip()
            if scn and len(scn) > 1:
                sentence_texts.add(scn)
    except:
        pass

total_unique = len(meaning_texts) + len(sentence_texts)
uncached_meanings = [t for t in meaning_texts if not text_cached(t, VOICE_ZH)]
uncached_sentences = [t for t in sentence_texts if not text_cached(t, VOICE_ZH)]

print(f"From 20000 words sample:")
print(f"  Unique meaning texts: {len(meaning_texts)}")
print(f"  Unique sentence texts: {len(sentence_texts)}")
print(f"  Uncached meanings: {len(uncached_meanings)} ({len(uncached_meanings)/len(meaning_texts)*100:.1f}%)")
print(f"  Uncached sentences: {len(uncached_sentences)} ({len(uncached_sentences)/len(sentence_texts)*100:.1f}%)")
print(f"  Total estimated for 205k words: ~{total_unique * 205000 // 20000} Chinese texts")
print(f"  Time estimate: ~{len(uncached_meanings) + len(uncached_sentences)} uncached ÷ 15/s × 2s = ~{(len(uncached_meanings) + len(uncached_sentences))/15*2:.0f}s")
print(f"  ≈ {(len(uncached_meanings) + len(uncached_sentences))/15*2/60:.0f} minutes")
