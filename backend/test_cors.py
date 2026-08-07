import urllib.request

req = urllib.request.Request(
    'http://localhost:8000/api/v1/agent/chat',
    method='OPTIONS',
    headers={
        'Origin': 'https://fine-analyst-ai.vercel.app',
        'Access-Control-Request-Method': 'POST'
    }
)
try:
    with urllib.request.urlopen(req) as res:
        print(f"Status: {res.status}")
        print("Headers:")
        for k, v in res.getheaders():
            print(f"  {k}: {v}")
except Exception as e:
    print(e)
