import requests

response = requests.post(
    "http://127.0.0.1:8000/api/v1/agent/chat",
    json={"message": "Show me total sales", "session_id": "test-session-123"}
)
print("Response 1:", response.status_code)

response = requests.post(
    "http://127.0.0.1:8000/api/v1/agent/chat",
    json={"message": "What about by month?", "session_id": "test-session-123"}
)
print("Response 2:", response.status_code)
print(response.text)
