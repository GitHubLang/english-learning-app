import subprocess
import base64

# Test from OUTSIDE - access cloud server directly
test_cases = [
    # Test 1: short texts (should all work)
    ["word", "abandon"],
    ["mean", "leave completely"],
    ["exam", "He abandoned family"],
    ["cn", "抛弃了家人"],
]

for i, (name, text) in enumerate(test_cases):
    import urllib.parse
    encoded = urllib.parse.quote(text)
    cmd = f'curl -s -o nul -w "%{{http_code}}" "http://124.221.212.61:8082/api/tts?text={encoded}&lang=en"'
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
    print(f'  {name}: {r.stdout.strip()}')

print()

# Now test concurrent from local
import urllib.parse
urls = []
for name, text in test_cases:
    encoded = urllib.parse.quote(text)
    urls.append(f'"http://124.221.212.61:8082/api/tts?text={encoded}&lang=en"')

# Using subprocess with background & in cmd
script_lines = ['@echo off']
for idx, url in enumerate(urls):
    script_lines.append(f'start /B curl -s -o nul -w "req{idx+1}: %%{{http_code}}%%\\n" {url}')
script_lines.append('timeout /t 10 > nul')
temp_script = '\n'.join(script_lines)

with open('D:\\myProject\\english-learning-app\\test_concurrent.bat', 'w') as f:
    f.write(temp_script)

r = subprocess.run(['D:\\myProject\\english-learning-app\\test_concurrent.bat'], shell=True, capture_output=True, text=True, timeout=15)
print('Concurrent results:')
print(r.stdout)
if r.stderr:
    print('ERR:', r.stderr[:500])
