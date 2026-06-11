import urllib.request
import time
import json

# Test the actual Flask API from local machine
BASE = 'http://localhost:8082'

# First get a token
t0 = time.time()
req = urllib.request.Request(
    f'{BASE}/api/auth/login',
    data=json.dumps({'username': 'test', 'password': 'test123'}).encode(),
    headers={'Content-Type': 'application/json'}
)
try:
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    token = data.get('token', '')
    t1 = time.time()
    print(f'Login: {t1-t0:.3f}s, token: {token[:20]}...')
except Exception as e:
    print(f'Login failed: {e}')
    # Try register
    t0 = time.time()
    req = urllib.request.Request(
        f'{BASE}/api/auth/register',
        data=json.dumps({'username': 'test', 'password': 'test123', 'textbook_id': 1}).encode(),
        headers={'Content-Type': 'application/json'}
    )
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    token = data.get('token', '')
    t1 = time.time()
    print(f'Register: {t1-t0:.3f}s, token: {token[:20]}...')

# Test random word for textbook 1 (small)
t0 = time.time()
req = urllib.request.Request(
    f'{BASE}/api/words/random?textbook_id=1',
    headers={'Authorization': f'Bearer {token}'}
)
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())
t1 = time.time()
response_size = len(json.dumps(data))
word = data.get('word', {})
print(f'\nRandom word (textbook 1, small): {t1-t0:.3f}s')
print(f'  Response size: {response_size} bytes ({response_size/1024:.1f} KB)')
print(f'  Has raw: {"raw" in word}')
print(f'  Has word_json: {"word_json" in word}')

# Test random word for textbook 82 (big)
t0 = time.time()
req = urllib.request.Request(
    f'{BASE}/api/words/random?textbook_id=82',
    headers={'Authorization': f'Bearer {token}'}
)
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())
t1 = time.time()
response_size = len(json.dumps(data))
word = data.get('word', {})
print(f'\nRandom word (textbook 82, 52k words): {t1-t0:.3f}s')
print(f'  Response size: {response_size} bytes ({response_size/1024:.1f} KB)')
print(f'  Has raw: {"raw" in word}')
print(f'  Has word_json: {"word_json" in word}')

# Test word detail (by ID)
t0 = time.time()
req = urllib.request.Request(
    f'{BASE}/api/words/1',
    headers={'Authorization': f'Bearer {token}'}
)
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())
t1 = time.time()
response_size = len(json.dumps(data))
print(f'\nWord detail (id=1): {t1-t0:.3f}s')
print(f'  Response size: {response_size} bytes ({response_size/1024:.1f} KB)')
print(f'  Has raw: {"raw" in data}')
print(f'  Has word_json: {"word_json" in data}')

# Test search
t0 = time.time()
req = urllib.request.Request(
    f'{BASE}/api/words/search?q=hello&limit=10',
    headers={'Authorization': f'Bearer {token}'}
)
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())
t1 = time.time()
response_size = len(json.dumps(data))
print(f'\nSearch "hello": {t1-t0:.3f}s')
print(f'  Results: {len(data.get("words", []))}')
print(f'  Response size: {response_size} bytes ({response_size/1024:.1f} KB)')

# Test search with more results
t0 = time.time()
req = urllib.request.Request(
    f'{BASE}/api/words/search?q=ab&limit=50',
    headers={'Authorization': f'Bearer {token}'}
)
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())
t1 = time.time()
response_size = len(json.dumps(data))
print(f'\nSearch "ab" (50 results): {t1-t0:.3f}s')
print(f'  Results: {len(data.get("words", []))}')
print(f'  Response size: {response_size} bytes ({response_size/1024:.1f} KB)')

# Test TTS (cached)
t0 = time.time()
req = urllib.request.Request(f'{BASE}/api/tts?text=hello&lang=en')
resp = urllib.request.urlopen(req)
t1 = time.time()
print(f'\nTTS "hello": {t1-t0:.3f}s')
print(f'  Response size: {len(resp.read())} bytes')
