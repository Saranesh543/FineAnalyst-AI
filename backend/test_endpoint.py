import urllib.request
import json
import sys

data = json.dumps({
    "message": "Analyze sales over time.",
    "context_messages": []
}).encode('utf-8')

req = urllib.request.Request(
    'http://127.0.0.1:8000/api/chat',
    data=data,
    headers={
        'Content-Type': 'application/json',
        'x-user-id': 'test-user',
        'x-session-id': 'test-session'
    }
)

try:
    res = urllib.request.urlopen(req)
    print(res.read().decode('utf-8'))
except Exception as e:
    print(f"Failed: {e}")
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
