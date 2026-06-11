"""Debug cache key mismatch between pre-cache script and autoPlay"""
import hashlib
import os
import re

BASE_DIR = "D:\\myProject\\english-learning-app"
CACHE_DIR = os.path.join(BASE_DIR, "cached_tts")
VOICE_ZH = "zh-CN-XiaoxiaoNeural"

def check(text, label=""):
    key = hashlib.md5("{}:{}".format(text, VOICE_ZH).encode()).hexdigest()
    subdir = key[:2]
    path = os.path.join(CACHE_DIR, subdir, "{}.mp3".format(key))
    exists = os.path.exists(path)
    mark = "OK" if exists else "MISS"
    print("  {}  {} -> [{}] {}".format(mark, label, key[:8], text))
    return exists

print("=== 预缓存格式(带词性) ===")
check("n 猫", "precache format")

print("\n=== autoPlay实际发送(过滤后) ===")
check("猫", "single meaning, filtered")

print("\n=== 多义组合 ===")
check("n 猫；v 猫；adj 猫似的", "joined meanings (server side)")

# Simulate what autoPlay does
text = "n 猫；v 猫；adj 猫似的"
cleaned = re.sub(
    r"\b(adj|adv|v\.?|n\.?|adj\.?|adv\.?|conj\.?|prep\.?|pron\.?|int\.?|aux\.?|modal\.?|det\.?)\b",
    "", text, flags=re.IGNORECASE
).strip()
print("\n=== autoPlay过滤后的文本 ===")
print("  raw: {!r}".format(text))
print("  after filter+trim: {!r}".format(cleaned))

check(cleaned, "autoPlay filtered")
check(cleaned.replace("  ", " "), "filtered+single spaces")
