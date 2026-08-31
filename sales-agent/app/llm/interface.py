from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_json(self, prompt: str, system_prompt: str = None) -> Dict[str, Any]:
        """
        Generates a JSON response from the LLM based on the prompt.
        Must guarantee a valid dictionary is returned.
        """
        pass

    @abstractmethod
    async def generate_text(self, prompt: str, system_prompt: str = None) -> str:
        """
        Generates standard text from the LLM.
        """
        pass
