from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseSearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Returns list of candidate sources:
        [
            {"url": "...", "title": "...", "snippet": "...", "source_type": "web_search"}
        ]
        """
        pass

class MockSearchProvider(BaseSearchProvider):
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        if "BonBon Supermarket" in query:
            return [
                {
                    "url": "https://bonbonsupermarket.com",
                    "title": "BonBon Supermarket - Official Website",
                    "snippet": "Welcome to BonBon Supermarket in Andheri. Call us at 098333 62100.",
                    "source_type": "web_search"
                },
                {
                    "url": "https://instagram.com/bonbonsupermarket",
                    "title": "BonBon Supermarket (@bonbonsupermarket)",
                    "snippet": "Instagram profile for BonBon.",
                    "source_type": "web_search"
                },
                {
                    "url": "https://api.whatsapp.com/send/?phone=919833362100",
                    "title": "Message on WhatsApp",
                    "snippet": "Chat with BonBon Supermarket.",
                    "source_type": "web_search"
                }
            ]
        return []
