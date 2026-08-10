import asyncio
import httpx

async def run():
    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {
            "question": """Month | Revenue | Expenses | Customers | Refunds | Complaints
Jan | 520000 | 310000 | 1200 | 32 | 18
Feb | 545000 | 325000 | 1360 | 35 | 21
Mar | 580000 | 340000 | 1410 | 41 | 25
Apr | 565000 | 350000 | 1340 | 38 | 19
May | 610000 | 365000 | 1420 | 45 | 27
Jun | 650000 | 380000 | 1510 | 48 | 29
Jul | 690000 | 395000 | 1590 | 52 | 31
Aug | 720000 | 410000 | 1660 | 75 | 48
Sep | 750000 | 420000 | 1730 | 57 | 32
Oct | 790000 | 440000 | 1820 | 57 | 30
Nov | 835000 | 455000 | 1900 | 94 | 54
Dec | 910000 | 480000 | 2100 | 49 | 26

Analyze this dataset and decide what charts would be most useful. Do not limit yourself to one chart. Find unusual trends, calculate useful metrics, identify relationships between variables, and explain any months that require investigation.""",
            "session_id": "test-session"
        }
        res = await client.post("http://127.0.0.1:8000/api/v1/analyze", json=payload)
        print(f"Status: {res.status_code}")
        try:
            print(res.json())
        except Exception as e:
            print(res.text)

asyncio.run(run())
