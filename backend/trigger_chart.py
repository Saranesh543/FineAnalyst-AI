import requests

response = requests.post(
    "http://127.0.0.1:8000/api/v1/agent/chat",
    json={"message": "generate a chart of sales by month"}
)
print("Response:", response.status_code)
print(response.text)
