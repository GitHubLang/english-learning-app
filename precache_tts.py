# -*- coding: utf-8 -*-
"""
英语学习 - TTS 发音预缓存工具
1. 迁移旧缓存到子目录结构
2. 优先缓存专八词汇
3. 缓存其他所有词汇
4. 缓存例句英文发音
"""
import mysql.connector
import asyncio
import edge_tts
import hashlib
import os
import sys
import json
import time
import re

# ========== 配置 ==========
DB_CONFIG = dict(host='192.168.71.189', user='root', password='notes123', database='english_db')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, 'cached_tts')
VOICE_EN = 'en-US-JennyNeural'
VOICE_ZH = 'zh-CN-XiaoxiaoNeural'
CONCURRENCY = 15
TTS_TIMEOUT = 30
TEM8_BOOK_IDS = [5, 10, 20]
LOG_FILE = os.path.join(BASE_DIR, 'precache_tts.log')

os.makedirs(CACHE_DIR, exist_ok=True)


# ========== 日志 ==========

def log(msg):
    ts = time.strftime('%m-%d %H:%M:%S')
    line = "[{}] {}".format(ts, msg)
    print(line)
    sys.stdout.flush()
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


# ========== 缓存工具 ==========

def get_cache_path(text, voice=VOICE_EN):
    key = hashlib.md5("{}:{}".format(text, voice).encode()).hexdigest()
    subdir = key[:2]
    dirpath = os.path.join(CACHE_DIR, subdir)
    os.makedirs(dirpath, exist_ok=True)
    return os.path.join(dirpath, "{}.mp3".format(key)), key


# ========== 迁移旧缓存 ==========

def migrate_old_cache():
    if not os.path.exists(CACHE_DIR):
        return 0, 0
    items = os.listdir(CACHE_DIR)
    mp3_files = [f for f in items if f.endswith('.mp3') and os.path.isfile(os.path.join(CACHE_DIR, f))]
    moved = 0
    import shutil
    for fname in mp3_files:
        old_path = os.path.join(CACHE_DIR, fname)
        cache_key = fname.replace('.mp3', '')
        subdir = cache_key[:2]
        new_dir = os.path.join(CACHE_DIR, subdir)
        os.makedirs(new_dir, exist_ok=True)
        new_path = os.path.join(new_dir, fname)
        try:
            if not os.path.exists(new_path):
                os.rename(old_path, new_path)
            else:
                os.remove(old_path)
            moved += 1
        except PermissionError:
            try:
                if not os.path.exists(new_path):
                    shutil.copy2(old_path, new_path)
                moved += 1
            except:
                pass
    return len(mp3_files), moved


# ========== 数据库 ==========

def get_words_for_books(book_ids, distinct=True):
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()
    ids_str = ','.join(str(i) for i in book_ids)
    distinct_clause = "DISTINCT" if distinct else ""
    sql = """
        SELECT {} LOWER(TRIM(word))
        FROM words
        WHERE textbook_id IN ({})
          AND word IS NOT NULL AND TRIM(word) != ''
          AND word REGEXP '^[a-zA-Z]'
        ORDER BY word
    """.format(distinct_clause, ids_str)
    cur.execute(sql)
    words = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return words


def get_all_words_exclude_books(exclude_book_ids):
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()
    exclude_str = ','.join(str(i) for i in exclude_book_ids)
    sql = """
        SELECT DISTINCT LOWER(TRIM(word))
        FROM words
        WHERE (textbook_id NOT IN ({}) OR textbook_id IS NULL)
          AND word IS NOT NULL AND TRIM(word) != ''
          AND word REGEXP '^[a-zA-Z]'
          AND LENGTH(TRIM(word)) BETWEEN 2 AND 30
        ORDER BY word
    """.format(exclude_str)
    cur.execute(sql)
    words = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return words


def get_example_sentences(book_ids=None):
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()
    if book_ids:
        ids_str = ','.join(str(i) for i in book_ids)
        sql = """
            SELECT word_json FROM words
            WHERE textbook_id IN ({})
              AND word_json IS NOT NULL AND word_json != ''
        """.format(ids_str)
    else:
        sql = """
            SELECT word_json FROM words
            WHERE word_json IS NOT NULL AND word_json != ''
        """
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    sentences = set()
    for (wj,) in rows:
        try:
            data = json.loads(wj)
            content = data.get('content', {})
            word_content = content.get('word', {}).get('content', {})
            sentence_data = word_content.get('sentence', {}).get('sentences', [])
            for s in sentence_data:
                en = (s.get('sContent') or '').strip()
                if en and len(en) > 5 and re.match(r'^[A-Za-z0-9\s\.,!?\'\"-]+$', en):
                    sentences.add(en)
        except:
            pass
    return list(sentences)


# ========== TTS 缓存 ==========

def _get_cache_path_sync(text, voice=VOICE_EN):
    key = hashlib.md5("{}:{}".format(text, voice).encode()).hexdigest()
    subdir = key[:2]
    return os.path.join(CACHE_DIR, subdir, "{}.mp3".format(key))


def text_cached(text, voice=VOICE_EN):
    return os.path.exists(_get_cache_path_sync(text, voice))


def text_cached_zh(text):
    return os.path.exists(_get_cache_path_sync(text, VOICE_ZH))


async def cache_text(text, voice=VOICE_EN, sem=None):
    path = _get_cache_path_sync(text, voice)
    if os.path.exists(path):
        return False
    try:
        communicate = edge_tts.Communicate(text, voice)
        await asyncio.wait_for(communicate.save(path), timeout=TTS_TIMEOUT)
        return True
    except asyncio.TimeoutError:
        log("  [TIMEOUT] {}: {}s timeout".format(text[:40], TTS_TIMEOUT))
        return False
    except Exception as e:
        log("  [FAIL] {}: {}".format(text[:40], e))
        return False


async def cache_word_batch(words, label, progress_stat, voice=VOICE_EN):
    sem = asyncio.Semaphore(CONCURRENCY)
    total = len(words)
    done = progress_stat[0]
    new_count = 0
    fail_count = 0

    async def _cached(word):
        async with sem:
            return await cache_text(word, voice)

    for i in range(0, total, 100):
        batch = words[i:i+100]
        tasks = [_cached(w) for w in batch]
        results = await asyncio.gather(*tasks)
        new_count += sum(1 for r in results if r)
        fail_count += sum(1 for r in results if r is False)
        done += len(batch)
        pct = done / (progress_stat[1] or 1) * 100
        elapsed = time.time() - progress_stat[2]
        rate = done / elapsed if elapsed > 0 else 0
        eta = (progress_stat[1] - done) / rate if rate > 0 else 0
        log("  [{}] {}/{} ({:.1f}%) | new={} skip={} fail={} | {:.1f}/s | ETA {:.0f}min".format(
            label, done, progress_stat[1], pct,
            new_count, done - new_count - fail_count, fail_count,
            rate, eta / 60))
    progress_stat[0] = done


def _extract_zh_from_word_json(rows):
    """从 word_json 行提取中文释义和例句"""
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
                    text = "{} {}".format(pos, cn).strip() if pos else cn
                    meanings.add(text)
            sdata = wc.get('sentence', {}).get('sentences', [])
            for s in sdata:
                scn = (s.get('sCn') or '').strip()
                if scn and len(scn) > 1:
                    sentences.add(scn)
        except:
            pass
    return meanings, sentences


def get_zh_texts(book_ids=None):
    """获取中文文本（释义+例句），可选限制课本"""
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()
    if book_ids:
        ids = ','.join(str(i) for i in book_ids)
        cur.execute("SELECT word_json FROM words WHERE textbook_id IN ({}) AND word_json IS NOT NULL AND word_json != ''".format(ids))
    else:
        cur.execute("SELECT word_json FROM words WHERE word_json IS NOT NULL AND word_json != ''")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    meanings, sentences = _extract_zh_from_word_json(rows)
    return list(meanings | sentences)


# ========== 主流程 ==========

async def main():
    log("=" * 65)
    log("  TTS Cache Prewarmer")
    log("=" * 65)
    start_time = time.time()

    # Step 0: migrate old cache
    log("[Step 0] Migrating old cache...")
    total_old, moved = migrate_old_cache()
    log("  old files: {}, moved: {}".format(total_old, moved))

    # Step 1: TEM-8 words
    log("[Step 1] Fetching TEM-8 words (IDs={})...".format(TEM8_BOOK_IDS))
    tem8_words = get_words_for_books(TEM8_BOOK_IDS, distinct=True)
    tem8_uncached = [w for w in tem8_words if not text_cached(w)]
    log("  TEM-8 total: {}, uncached: {}".format(len(tem8_words), len(tem8_uncached)))
    if tem8_uncached:
        progress = [0, len(tem8_words), start_time]
        await cache_word_batch(tem8_uncached, "tem8", progress)

    # Step 2: other words
    log("[Step 2] Fetching non-TEM-8 words...")
    other_words = get_all_words_exclude_books(TEM8_BOOK_IDS)
    other_uncached = [w for w in other_words if not text_cached(w)]
    log("  other total: {}, uncached: {}".format(len(other_words), len(other_uncached)))
    if other_uncached:
        total_remaining = len(tem8_words) + len(other_words)
        progress = [len(tem8_words), total_remaining, start_time]
        await cache_word_batch(other_uncached, "all", progress)

    # Step 3: sentences
    log("[Step 3] Extracting sentences...")

    tem8_sentences = get_example_sentences(TEM8_BOOK_IDS)
    sent_uncached = [s for s in tem8_sentences if not text_cached(s)]
    log("  TEM-8 sentences: {}, uncached: {}".format(len(tem8_sentences), len(sent_uncached)))
    if sent_uncached:
        progress = [0, len(sent_uncached), time.time()]
        await cache_word_batch(sent_uncached, "tem8-sent", progress)

    all_sentences = get_example_sentences()
    all_sent_uncached = [s for s in all_sentences if not text_cached(s)]
    log("  all sentences: {}, uncached: {}".format(len(all_sentences), len(all_sent_uncached)))
    if all_sent_uncached:
        progress = [0, len(all_sent_uncached), time.time()]
        await cache_word_batch(all_sent_uncached, "all-sent", progress)

    # Step 4a: Chinese voice for TEM-8 books (priority)
    log("[Step 4a] Caching TEM-8 Chinese texts with zh voice (IDs={})...".format(TEM8_BOOK_IDS))
    tem8_zh = get_zh_texts(TEM8_BOOK_IDS)
    tem8_zh_uncached = [t for t in tem8_zh if not text_cached(t, VOICE_ZH)]
    log("  TEM-8 Chinese total: {}, uncached: {}".format(len(tem8_zh), len(tem8_zh_uncached)))
    if tem8_zh_uncached:
        progress = [0, len(tem8_zh_uncached), time.time()]
        await cache_word_batch(tem8_zh_uncached, "tem8-zh", progress, voice=VOICE_ZH)

    # Step 4b: remaining Chinese voice (all books)
    log("[Step 4b] Caching remaining Chinese texts with zh voice...")
    all_zh = get_zh_texts()
    all_zh_uncached = [t for t in all_zh if not text_cached(t, VOICE_ZH)]
    log("  All Chinese total: {}, uncached: {}".format(len(all_zh), len(all_zh_uncached)))
    if all_zh_uncached:
        progress = [0, len(all_zh_uncached), time.time()]
        await cache_word_batch(all_zh_uncached, "all-zh", progress, voice=VOICE_ZH)

    # Done
    elapsed = time.time() - start_time
    log("=" * 65)
    log("  DONE! Elapsed {:.1f} min".format(elapsed / 60))
    log("=" * 65)

    total_mp3 = 0
    for root, dirs, files in os.walk(CACHE_DIR):
        total_mp3 += len([f for f in files if f.endswith('.mp3')])
    log("  total MP3 files: {}".format(total_mp3))

    dir_counts = []
    for item in os.listdir(CACHE_DIR):
        d = os.path.join(CACHE_DIR, item)
        if os.path.isdir(d):
            mp3_count = len([f for f in os.listdir(d) if f.endswith('.mp3')])
            dir_counts.append((item, mp3_count))
    dir_counts.sort()
    if dir_counts:
        counts = [c for _, c in dir_counts]
        log("  subdirs: {}, min={}, avg={:.0f}, max={}".format(
            len(dir_counts), min(counts), sum(counts)/len(counts), max(counts)))


if __name__ == '__main__':
    asyncio.run(main())
