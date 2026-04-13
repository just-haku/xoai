"""LLM Provider implementations (Gemini, OpenAI, etc.)."""

import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

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


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    async def chat_stream(self, model, messages, tools=None, temperature=0.7) -> AsyncIterator[str]:
        # Convert messages to Gemini format (handled by SDK basically)
        # Note: the new google-genai SDK has a slightly different pattern
        # TODO: Refine based on actual SDK response structure
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
