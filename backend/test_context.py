import requests
import json

URL = "http://127.0.0.1:8000/api/v1/analyze"

def analyze(question):
    print(f"\n--- Question: {question} ---")
    resp = requests.post(URL, json={"question": question})
    if resp.status_code == 200:
        data = resp.json()
        print(f"SQL Generated:\n{data.get('sql', 'None')}")
    else:
        print(f"Error {resp.status_code}: {resp.text}")

q1 = "Show me EU customers"
analyze(q1)

q2 = "What's our top product?"
context2 = f"Previous context from conversation history: [{q1}]. New question: \"{q2}\". Please answer the new question fully incorporating the previous context where relevant."
analyze(context2)

q3 = "Break the EU number down by region"
context3 = f"Previous context from conversation history: [{q1} | {q2}]. New question: \"{q3}\". Please answer the new question fully incorporating the previous context where relevant."
analyze(context3)
