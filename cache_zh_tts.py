"""
缓存中文TTS：队列模式，避免单个慢请求卡住全批。
只缓存 autoPlay 实际发送格式的文本（含义+例句翻译）。
"""
import mysql.connector
import json
import re
import hashlib
import os
import asyncio
import edge_tts
import time
import sys
import signal

DB_CONFIG = dict(host='192.168.71.189', user='root', password='notes123', database='english_db')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, 'cached_tts')
VOICE_ZH = 'zh-CN-XiaoxiaoNeural'
VOICE_EN = 'en-US-JennyNeural'
CONCURRENCY = 30
TTS_TIMEOUT = 30
STATUS_FILE = os.path.join(BASE_DIR, 'cache_zh_status.json')
KILL_FILE = os.path.join(BASE_DIR, 'cache_zh_kill.txt')

POS_PATTERN = re.compile(
    r'\b(adj|adv|v\.?|n\.?|adj\.?|adv\.?|conj\.?|prep\.?|pron\.?|int\.?|aux\.?|modal\.?|det\.?)\b',
    re.IGNORECASE
)

def auto_play_filter(text):
    if not text: return ''
    cleaned = POS_PATTERN.sub('', text).strip()
    return cleaned if cleaned else text

def is_chinese(text):
    return bool(re.search(r'[\u4e00-\u9fff]', text))

def get_meaning(wj):
    try:
        data = json.loads(wj)
        wc = data.get('content', {}).get('word', {}).get('content', {})
        trans = wc.get('trans', [])
        meanings = []
        for t in trans:
            pos = t.get('pos', '')
            tran_cn = t.get('tranCn', '').strip()
            if tran_cn:
                meanings.append(f"{pos} {tran_cn}" if pos else tran_cn)
        return '；'.join(meanings) if meanings else ''
    except:
        return ''

def get_example_cn(wj):
    try:
        data = json.loads(wj)
        wc = data.get('content', {}).get('word', {}).get('content', {})
        for sent in wc.get('sentence', {}).get('sentences', [])[:5]:
            scn = (sent.get('sCn') or '').strip()
            if scn:
                return scn
    except:
        pass
    return ''

def get_first_example_en(wj):
    try:
        data = json.loads(wj)
        wc = data.get('content', {}).get('word', {}).get('content', {})
        for sent in wc.get('sentence', {}).get('sentences', [])[:5]:
            en = (sent.get('sContent') or '').strip()
            if en:
                return en
    except:
        pass
    return ''

def is_cached(text, voice):
    key = hashlib.md5(f"{text}:{voice}".encode()).hexdigest()
    subdir = key[:2]
    return os.path.exists(os.path.join(CACHE_DIR, subdir, f"{key}.mp3"))

def get_cache_path(text, voice):
    key = hashlib.md5(f"{text}:{voice}".encode()).hexdigest()
    subdir = key[:2]
    d = os.path.join(CACHE_DIR, subdir)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{key}.mp3")

def write_status(stats):
    with open(STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f)

async def cache_one(text, voice):
    """缓存单个文本，返回 True/False"""
    path = get_cache_path(text, voice)
    if os.path.exists(path):
        return True  # already cached
    try:
        communicate = edge_tts.Communicate(text, voice)
        await asyncio.wait_for(communicate.save(path), timeout=TTS_TIMEOUT)
        return True
    except:
        return False

async def cache_worker(queue, sem, stats):
    """Worker: 从队列取任务，缓存，更新统计"""
    while True:
        try:
            text, voice = await asyncio.wait_for(queue.get(), timeout=5)
        except asyncio.TimeoutError:
            return  # queue empty
        
        ok = False
        async with sem:
            ok = await cache_one(text, voice)
        
        stats['attempted'] += 1
        if ok:
            stats['cached'] += 1
        else:
            stats['failed'] += 1
        
        queue.task_done()

async def main():
    t0 = time.time()
    t_progress = time.time()
    
    # 清理 kill file
    if os.path.exists(KILL_FILE):
        os.remove(KILL_FILE)
    
    # Phase 1: scan
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM words WHERE word_json IS NOT NULL AND word_json != ''")
    total = cur.fetchone()[0]
    
    all_texts = set()
    BATCH = 5000
    offset = 0
    
    print(f"[{time.strftime('%H:%M:%S')}] Scan {total} words...")
    
    while offset < total:
        cur.execute(
            "SELECT word_json FROM words WHERE word_json IS NOT NULL AND word_json != '' LIMIT %s OFFSET %s",
            (BATCH, offset)
        )
        rows = cur.fetchall()
        for (wj,) in rows:
            meaning = get_meaning(wj)
            if meaning:
                filtered = auto_play_filter(meaning)
                if is_chinese(filtered):
                    all_texts.add((filtered, VOICE_ZH))
            cn = get_example_cn(wj)
            if cn:
                all_texts.add((cn, VOICE_ZH))
        offset += len(rows)
    cur.close()
    conn.close()
    
    print(f"[{time.strftime('%H:%M:%S')}] Unique ZH texts: {len(all_texts)}")
    
    # Filter already cached
    to_cache = [(t, v) for t, v in all_texts if not is_cached(t, v)]
    print(f"  Already cached: {len(all_texts) - len(to_cache)}")
    print(f"  Needs cache: {len(to_cache)}")
    
    if not to_cache:
        print("✅ All cached!")
        write_status({'total': 0, 'cached': 0, 'failed': 0, 'done': True, 'msg': 'All cached'})
        return
    
    # Phase 2: cache via queue
    queue = asyncio.Queue()
    for item in to_cache:
        await queue.put(item)
    
    sem = asyncio.Semaphore(CONCURRENCY)
    stats = {'attempted': 0, 'cached': 0, 'failed': 0}
    
    workers = [asyncio.create_task(cache_worker(queue, sem, stats)) for _ in range(CONCURRENCY * 2)]
    
    print(f"[{time.strftime('%H:%M:%S')}] Caching {len(to_cache)} texts ({CONCURRENCY} concurrent)...")
    
    # Progress reporter
    last_cached = 0
    write_status({'total': len(to_cache), 'cached': 0, 'failed': 0, 'done': False, 'eta_min': 0})
    
    while not queue.empty():
        await asyncio.sleep(30)  # report every 30 seconds
        
        if os.path.exists(KILL_FILE):
            print(f"\n[{time.strftime('%H:%M:%S')}] Kill file detected, shutting down...")
            break
        
        elapsed = time.time() - t0
        rate = stats['attempted'] / elapsed if elapsed > 0 else 0
        remaining = len(to_cache) - stats['attempted']
        eta = remaining / rate if rate > 0 else 0
        
        # Detect stall
        if stats['cached'] == last_cached and elapsed > 120:
            print(f"  ⚠️  No progress for {elapsed/60:.0f} min, check network")
        last_cached = stats['cached']
        
        pct = stats['attempted'] * 100 // len(to_cache)
        print(f"[{time.strftime('%H:%M:%S')}] {stats['attempted']}/{len(to_cache)} ({pct}%) "
              f"| ok={stats['cached']} fail={stats['failed']} "
              f"| {rate:.1f}/s | eta {eta/60:.0f}min")
        
        write_status({
            'total': len(to_cache),
            'cached': stats['cached'],
            'failed': stats['failed'],
            'done': False,
            'eta_min': eta / 60,
            'pct': pct,
            'rate': round(rate, 1)
        })
    
    # Wait for remaining
    await queue.join()
    
    # Cancel workers
    for w in workers:
        w.cancel()
    
    elapsed = time.time() - t0
    print(f"\n[{time.strftime('%H:%M:%S')}] ✅ Done! {elapsed/60:.0f} min")
    print(f"  Cached: {stats['cached']}  Failed: {stats['failed']}")
    
    write_status({
        'total': len(to_cache),
        'cached': stats['cached'],
        'failed': stats['failed'],
        'done': True,
        'elapsed_min': elapsed / 60
    })

if __name__ == '__main__':
    asyncio.run(main())
