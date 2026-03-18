# Please install OpenAI SDK first: `pip3 install openai`
import os
from openai import OpenAI

api_key = os.environ.get('DEEPSEEK_API_KEY', '').strip()
if not api_key:
    raise RuntimeError('Please set environment variable DEEPSEEK_API_KEY first.')

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com")

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
    ],
    stream=False
)

print(response.choices[0].message.content)
