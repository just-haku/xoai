"""LLM Provider implementations (Gemini, OpenAI, etc.)."""

import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

import httpx
from google import genai
from google.genai import types
from openai import AsyncOpenAI

logger = logging.getLogger("xoai.agents.providers")


class LLMProvider(ABC):
    @abstractmethod
    async def chat_stream(
        self, 
        model: str, 
        messages: list[dict], 
        tools: list[Any] | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream chat completions from the provider."""
        pass

    @abstractmethod
    async def chat(
        self,
        model: str,
        messages: list[dict],
        tools: list[Any] | None = None,
        temperature: float = 0.7,
    ) -> dict:
        """Non-streaming chat completion."""
        pass

    @abstractmethod
    async def list_models(self) -> list[str]:
        """List available model IDs from the provider."""
        pass


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)

    async def chat_stream(self, model, messages, tools=None, temperature=0.7) -> AsyncIterator[str]:
        response = await self.client.aio.models.generate_content_stream(
            model=model,
            contents=messages,
            config=types.GenerateContentConfig(
                temperature=temperature,
                tools=tools,
            )
        )
        async for chunk in response:
            if chunk.text:
                yield chunk.text

    async def chat(self, model, messages, tools=None, temperature=0.7) -> dict:
        response = await self.client.aio.models.generate_content(
            model=model,
            contents=messages,
            config=types.GenerateContentConfig(
                temperature=temperature,
                tools=tools,
            )
        )
        return {
            "content": response.text,
            "tool_calls": response.candidates[0].content.parts[0].function_call if response.candidates else None,
        }

    async def list_models(self) -> list[str]:
        url = "https://generativelanguage.googleapis.com/v1beta/models"
        params = {"key": self.api_key}

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()

            data = response.json()
            models: list[str] = []
            for model in data.get("models", []):
                if "generateContent" not in model.get("supportedGenerationMethods", []):
                    continue

                model_name = model.get("name", "")
                if model_name.startswith("models/"):
                    model_name = model_name[len("models/"):]
                if model_name:
                    models.append(model_name)

            return models
        except httpx.HTTPStatusError as e:
            detail = e.response.text.strip()
            logger.error("Gemini list_models HTTP error: %s", detail)
            raise ValueError(f"Gemini API error: {e.response.status_code} {detail}") from e
        except Exception as e:
            logger.error("Gemini list_models error: %s", e)
            raise ValueError(f"Gemini model fetch failed: {e}") from e


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str | None = None):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def chat_stream(self, model, messages, tools=None, temperature=0.7) -> AsyncIterator[str]:
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            temperature=temperature,
            stream=True
        )
        async for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    async def chat(self, model, messages, tools=None, temperature=0.7) -> dict:
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            temperature=temperature,
        )
        msg = response.choices[0].message
        return {
            "content": msg.content,
            "tool_calls": msg.tool_calls,
        }

    async def list_models(self) -> list[str]:
        try:
            # For Ollama/Custom, we might need to handle base_url specifically 
            # but standard OpenAI models.list() usually works if compliant
            response = await self.client.models.list()
            return [m.id for m in response.data]
        except Exception as e:
            logger.error("OpenAI list_models error: %s", e)
            raise ValueError(f"OpenAI model fetch failed: {e}") from e
