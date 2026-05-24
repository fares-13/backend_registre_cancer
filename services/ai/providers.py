import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


class MistralProvider:
    def __init__(self, api_key=None, model=None):
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY", "")
        self.model = model or os.getenv("MISTRAL_MODEL", "mistral-small-latest")

    @property
    def is_available(self):
        return bool(self.api_key)

    def chat_completion(self, messages, response_format=None, temperature=0, max_tokens=500):
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        request = Request(
            "https://api.mistral.ai/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))

        content = data["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        return content


class OpenAIProvider:
    def __init__(self, api_key=None, model=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    @property
    def is_available(self):
        return bool(self.api_key)

    def chat_completion(self, messages, response_format=None, temperature=0, max_tokens=500):
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key)
        kwargs = {
            "model": self.model,
            "input": messages,
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if response_format:
            kwargs["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": "extraction",
                    "schema": response_format,
                    "strict": True,
                }
            }
        response = client.responses.create(**kwargs)
        return response.output_text


def get_provider():
    mistral = MistralProvider()
    if mistral.is_available:
        return mistral
    openai = OpenAIProvider()
    if openai.is_available:
        return openai
    return None
