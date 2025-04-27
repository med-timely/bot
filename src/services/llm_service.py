import json
import logging

import aiohttp
import aiohttp.client_exceptions
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Constants for OpenRouter configuration
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1/"
DEFAULT_MODEL = "mistralai/mistral-7b-instruct:free"
APP_DOMAIN = "https://medtimely.ru"
APP_NAME = "MedTimely"


class LLMRequest(BaseModel):
    prompt: str
    model: str | None = None
    temperature: float = 0.3
    max_tokens: int = 500


class LLMService:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str | None = None,
        default_model: str | None = None,
        timeout: int = 30,
    ):
        base_url = base_url or DEFAULT_BASE_URL
        default_model = default_model or DEFAULT_MODEL

        self.default_model = default_model
        self.session = aiohttp.ClientSession(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": APP_DOMAIN,
                "X-Title": APP_NAME,
            },
            timeout=aiohttp.ClientTimeout(total=timeout),
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def complete(self, request: LLMRequest) -> str:
        async with self.session.post(
            "chat/completions",
            json={
                "model": request.model or self.default_model,
                "messages": [{"role": "user", "content": request.prompt}],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            },
        ) as response:
            response.raise_for_status()
            try:
                data = await response.json()
                return data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                # Handle errors in response format
                raise ValueError(f"Invalid response format from LLM API: {e}") from e

    async def close(self):
        await self.session.close()
