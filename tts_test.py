import subprocess
import base64

script = """#!/bin/bash
grep -A10 "Database pool\|MySQLConnectionPool\|pool_name" /home/ubuntu/english-app/app.py
echo "---"
grep -A5 "def get_db" /home/ubuntu/english-app/app.py
"""
b64 = base64.b64encode(script.encode()).decode()
cmd = ['ssh', '-i', 'C:\\Users\\ADMIN\\.ssh\\tx01.pem', 'ubuntu@124.221.212.61',
       f'echo {b64} | base64 -d > /tmp/check_db.sh && chmod +x /tmp/check_db.sh && bash /tmp/check_db.sh']
r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
print(r.stdout)
