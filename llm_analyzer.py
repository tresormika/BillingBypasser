#!/usr/bin/env python3
"""
LLM Analyzer for BillingBypasser
Provides unified interface to multiple LLM APIs using requests.
"""

import os
import json
import requests
from typing import Dict, Any, Optional

class LLMProvider:
    """Base class for LLM providers."""
    def __init__(self, api_key: str):
        self.api_key = api_key

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        raise NotImplementedError

class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        super().__init__(api_key)
        self.model = model
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        if system_prompt:
            payload["system_instruction"] = {"parts": [{"text": system_prompt}]}
        response = requests.post(self.url, json=payload)
        if response.status_code == 200:
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            raise Exception(f"Gemini API error: {response.text}")

class OpenRouterProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "openai/gpt-4o"):
        super().__init__(api_key)
        self.model = model
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages
        }
        response = requests.post(self.url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"OpenRouter error: {response.text}")

class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        super().__init__(api_key)
        self.model = model
        self.url = "https://api.anthropic.com/v1/messages"

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}]
        }
        if system_prompt:
            payload["system"] = system_prompt
        response = requests.post(self.url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()["content"][0]["text"]
        else:
            raise Exception(f"Claude error: {response.text}")

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        super().__init__(api_key)
        self.model = model
        self.url = "https://api.openai.com/v1/chat/completions"

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages
        }
        response = requests.post(self.url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"OpenAI error: {response.text}")

class DeepSeekProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        super().__init__(api_key)
        self.model = model
        self.url = "https://api.deepseek.com/v1/chat/completions"

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages
        }
        response = requests.post(self.url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"DeepSeek error: {response.text}")

# Factory
def get_llm_provider(provider_name: str, api_key: str, model: str = None) -> LLMProvider:
    provider_name = provider_name.lower()
    if provider_name == "gemini":
        return GeminiProvider(api_key, model or "gemini-2.0-flash")
    elif provider_name == "openrouter":
        return OpenRouterProvider(api_key, model or "openai/gpt-4o")
    elif provider_name == "claude":
        return ClaudeProvider(api_key, model or "claude-3-5-sonnet-20241022")
    elif provider_name == "openai":
        return OpenAIProvider(api_key, model or "gpt-4o")
    elif provider_name == "deepseek":
        return DeepSeekProvider(api_key, model or "deepseek-chat")
    else:
        raise ValueError(f"Unknown provider: {provider_name}")