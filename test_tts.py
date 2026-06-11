import urllib.request
import urllib.parse
import time

BASE = 'http://localhost:8082'

def test_tts(label, text, lang):
    url = f'{BASE}/api/tts?text={urllib.parse.quote(text)}&lang={lang}'
    t0 = time.time()
    req = urllib.request.Request(url)
    resp = urllib.request.urlopen(req)
    body = resp.read()
    t1 = time.time()
    cached = 'HIT' if (t1-t0) < 0.1 else 'MISS'
    print(f'{cached} {lang} "{label}": {t1-t0:.3f}s, {len(body)}b')
    return t1 - t0, len(body)

# Test real app format: meaning without dot after pos
test_tts('EN word', 'hello', 'en')
test_tts('EN word2', 'apple', 'en')
test_tts('ZH meaning (no dot)', 'n 猫', 'zh')
test_tts('ZH meaning (no dot)', 'v 通风', 'zh')
test_tts('ZH meaning (no dot)', 'n 繁荣', 'zh')
test_tts('ZH long sentence', '窗外有一只可爱的猫', 'zh')

# Test key: does the actual app meaning format work?
# The app sends meaning like "n 猫" then after autoPlay filter, it removes POS patterns
# Let me test what the actual play queue sends
# The frontend filters out POS markers: adj, adv, v, n, etc.
# But meaning starts with pos without dot like 'n 猫' 
# The filter regex: /\b(adj|adv|v\.?|n\.?|...)/gi
# Since the format is 'n 猫' (no dot), 'n' at the start won't be matched as a word boundary without a space before
# Let me test the actual cleaned text
test_tts('ZH meaning filtered', '猫', 'zh')
test_tts('EN example', 'The cat is on the table', 'en')
test_tts('ZH example', '猫在桌子上', 'zh')
