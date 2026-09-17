import os
import json
from typing import Dict, Any
from app.llm.interface import BaseLLMProvider
from app.llm.mock_provider import MockLLMProvider
import logging

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

logger = logging.getLogger(__name__)

class GroqLLMProvider(BaseLLMProvider):
    def __init__(self, model_name: str = "llama-3.1-8b-instant"):
        self.model_name = model_name
        self.api_key = os.getenv("GROQ_API_KEY")
        if HAS_GROQ and self.api_key and self.api_key.strip():
            self.client = Groq(api_key=self.api_key)
        else:
            self.client = None
            logger.info("GROQ_API_KEY not configured. Using MockLLMProvider fallback.")
        self.fallback = MockLLMProvider()

    async def generate_json(self, prompt: str, system_prompt: str = None) -> Dict[str, Any]:
        if not self.client:
            return await self.fallback.generate_json(prompt, system_prompt)
            
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt + "\nYou MUST return valid JSON ONLY. No markdown wrappers."})
        messages.append({"role": "user", "content": prompt})
        
        try:
            import asyncio
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model_name,
                messages=messages
            )
            content = response.choices[0].message.content
            
            # Clean up markdown JSON wrappers if present
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            return json.loads(content)
        except Exception as e:
            logger.warning(f"Groq API call failed ({e}). Falling back to MockLLMProvider.")
            return await self.fallback.generate_json(prompt, system_prompt)

    async def generate_text(self, prompt: str, system_prompt: str = None) -> str:
        if not self.client:
            return await self.fallback.generate_text(prompt, system_prompt)
            
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            import asyncio
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model_name,
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"Groq API call failed ({e}). Falling back to MockLLMProvider.")
            return await self.fallback.generate_text(prompt, system_prompt)
