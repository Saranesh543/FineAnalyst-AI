import urllib.request
import json
import time

def test_analyze(question: str):
    req = urllib.request.Request(
        'http://localhost:8000/api/v1/analyze',
        method='POST',
        data=json.dumps({"question": question}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    start = time.time()
    try:
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode())
            print(f"[{question}] Status: {res.status} | Time: {(time.time() - start)*1000:.0f}ms")
            print(f"  Intent: {data.get('intent')}")
            print(f"  Steps: {[s.get('name') for s in data.get('steps', [])]}")
    except Exception as e:
        print(f"[{question}] Error: {e}")

test_analyze("hi")
test_analyze("thank you")
test_analyze("total revenue")
