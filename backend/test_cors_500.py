import urllib.request
import urllib.error
import json

req = urllib.request.Request(
    'http://localhost:8000/api/v1/agent/chat',
    method='POST',
    data=json.dumps({"message": "test", "session_id": "test"}).encode('utf-8'),
    headers={
        'Origin': 'https://fine-analyst-ai.vercel.app',
        'Content-Type': 'application/json'
    }
)
try:
    with urllib.request.urlopen(req) as res:
        print(f"Status: {res.status}")
        for k, v in res.getheaders():
            print(f"  {k}: {v}")
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code}")
    for k, v in e.headers.items():
        print(f"  {k}: {v}")
except Exception as e:
    print(e)
