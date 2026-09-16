import asyncio
import httpx
import json

class StripModelTransport(httpx.AsyncBaseTransport):
    def __init__(self, transport: httpx.AsyncBaseTransport):
        self.transport = transport

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        # Read the body since it's already serialized in memory
        body_bytes = request.content
        if body_bytes and b'"model"' in body_bytes:
            data = json.loads(body_bytes)
            if data.get("model") == "auto":
                del data["model"]
            new_body = json.dumps(data).encode("utf-8")
            
            # Create a new request with the updated body and proper content-length
            new_headers = request.headers.copy()
            new_headers["content-length"] = str(len(new_body))
            
            request = httpx.Request(
                method=request.method,
                url=request.url,
                headers=new_headers,
                content=new_body,
            )
        return await self.transport.handle_async_request(request)

async def main():
    transport = StripModelTransport(httpx.AsyncHTTPTransport())
    async with httpx.AsyncClient(transport=transport) as client:
        # Test 1: with model auto (stripped)
        print("Sending request with model='auto' (should be stripped by transport)")
        try:
            resp = await client.post('http://localhost:20128/v1/chat/completions', json={'model': 'auto', 'messages': [{'role': 'user', 'content': 'test'}]}, headers={'Authorization': 'Bearer test'})
            print("Response:", resp.status_code, resp.text)
        except Exception as e:
            print("Exception:", e)

    # Test 2: pure un-stripped
    async with httpx.AsyncClient() as client:
        print("Sending request with model='auto' (NOT stripped)")
        try:
            resp = await client.post('http://localhost:20128/v1/chat/completions', json={'model': 'auto', 'messages': [{'role': 'user', 'content': 'test'}]}, headers={'Authorization': 'Bearer test'}, timeout=3.0)
            print("Response:", resp.status_code, resp.text)
        except Exception as e:
            print("Exception:", e)

if __name__ == "__main__":
    asyncio.run(main())
