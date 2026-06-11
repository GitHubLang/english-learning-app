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

# Get ALL words
conn = mysql.connector.connect(host='192.168.71.189', user='root', password='notes123', database='english_db')
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM words WHERE word_json IS NOT NULL AND word_json != ''")
print(f"Total words with word_json: {cur.fetchone()[0]}")

cur.execute("SELECT DISTINCT textbook_id FROM words WHERE word_json IS NOT NULL AND word_json != '' ORDER BY textbook_id")
book_ids = [r[0] for r in cur.fetchall()]
print(f"Textbooks with word_json: {len(book_ids)}")

# Sample all unique Chinese texts from word_json
all_meaning_texts = set()
all_sentence_texts = set()
batch_size = 5000
offset = 0
total_processed = 0

t0 = time.time()
while True:
    cur.execute("SELECT word_json FROM words WHERE word_json IS NOT NULL AND word_json != '' LIMIT %s OFFSET %s", (batch_size, offset))
    rows = cur.fetchall()
    if not rows:
        break
    
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
                    all_meaning_texts.add(f"{pos} {cn}".strip() if pos else cn)
            sdata = wc.get('sentence', {}).get('sentences', [])
            for s in sdata:
                scn = (s.get('sCn') or '').strip()
                if scn and len(scn) > 1:
                    all_sentence_texts.add(scn)
        except:
            pass
    
    total_processed += len(rows)
    offset += batch_size
    elapsed = time.time() - t0
    print(f"  processed {total_processed} rows ({elapsed:.0f}s) | meanings={len(all_meaning_texts)} sentences={len(all_sentence_texts)}")

cur.close()
conn.close()

# Check cache status
uncached_meanings = [t for t in all_meaning_texts if not text_cached(t, VOICE_ZH)]
uncached_sentences = [t for t in all_sentence_texts if not text_cached(t, VOICE_ZH)]

print(f"\n=== ZH CACHE STATUS ===")
print(f"Unique meaning texts: {len(all_meaning_texts)}")
print(f"Unique sentence texts: {len(all_sentence_texts)}")
print(f"Uncached meanings: {len(uncached_meanings)} ({len(uncached_meanings)/len(all_meaning_texts)*100:.1f}%)")
print(f"Uncached sentences: {len(uncached_sentences)} ({len(uncached_sentences)/len(all_sentence_texts)*100:.1f}%)")

if uncached_meanings:
    print(f"\nSample uncached meanings:")
    for t in list(uncached_meanings)[:10]:
        print(f"  [{len(t)}c] {t}")
if uncached_sentences:
    print(f"\nSample uncached sentences:")
    for t in list(uncached_sentences)[:10]:
        print(f"  [{len(t)}c] {t}")

print(f"\nTotal uncached ZH texts: {len(uncached_meanings) + len(uncached_sentences)}")
print(f"\nEstimated cache time: {(len(uncached_meanings) + len(uncached_sentences)) / 15 * 2 / 60:.0f} min @ 15 concurrent, avg 2s each")
