import urllib.request
import json
import sys

data = json.dumps({
    "question": "Analyze sales over time.",
    "session_id": "test-session",
    "history": []
}).encode('utf-8')

req = urllib.request.Request(
    'http://127.0.0.1:8000/api/v1/analyze',
    data=data,
    headers={
        'Content-Type': 'application/json',
        'x-user-id': 'test-user',
        'x-session-id': 'test-session',
        'Authorization': 'Bearer placeholder'
    }
)

try:
    res = urllib.request.urlopen(req)
    print(res.read().decode('utf-8'))
except Exception as e:
    print(f"Failed: {e}")
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
