import urllib.request
import json
import time

req = urllib.request.Request(
    'http://localhost:8000/api/v1/agent/chat',
    method='POST',
    data=json.dumps({"message": "who are our top customers", "session_id": "test_session", "history": []}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

try:
    print("Testing chat endpoint without history...")
    with urllib.request.urlopen(req) as res:
        print(f"Status: {res.status}")
        
    print("Testing chat endpoint WITH history...")
    req_history = urllib.request.Request(
        'http://localhost:8000/api/v1/agent/chat',
        method='POST',
        data=json.dumps({
            "message": "and what about the worst?", 
            "session_id": "test_session",
            "history": [{"role": "user", "content": "who are our top customers"}, {"role": "assistant", "content": "Here are the top customers."}]
        }).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req_history) as res2:
        print(f"Status: {res2.status}")
        
except Exception as e:
    print(f"Error: {e}")
