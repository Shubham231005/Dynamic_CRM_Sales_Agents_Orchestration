import os
import json
from typing import Dict, Any
from app.llm.interface import BaseLLMProvider
import logging

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

logger = logging.getLogger(__name__)

class GeminiLLMProvider(BaseLLMProvider):
    def __init__(self, model_name: str = "gemini-2.5-pro"):
        self.model_name = model_name
        if HAS_GENAI:
            # Assumes GEMINI_API_KEY is in the environment
            self.client = genai.Client()
        else:
            self.client = None
            logger.warning("google-genai package not installed. GeminiLLMProvider will fail.")

    async def generate_json(self, prompt: str, system_prompt: str = None) -> Dict[str, Any]:
        if not self.client:
            raise RuntimeError("Gemini SDK not installed.")
            
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
        )
        if system_prompt:
            config.system_instruction = system_prompt
            
        try:
            # We use to_thread to keep it async friendly since the SDK might be sync
            import asyncio
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=config
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            raise

    async def generate_text(self, prompt: str, system_prompt: str = None) -> str:
        if not self.client:
            raise RuntimeError("Gemini SDK not installed.")
            
        config = types.GenerateContentConfig()
        if system_prompt:
            config.system_instruction = system_prompt
            
        try:
            import asyncio
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=config
            )
            return response.text
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            raise
