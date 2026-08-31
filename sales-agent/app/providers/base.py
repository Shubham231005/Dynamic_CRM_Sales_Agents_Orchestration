from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseLeadProvider(ABC):
    @abstractmethod
    async def search_businesses(self, industry: str, location: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Search for businesses based on industry and location.
        Returns a list of dictionaries containing raw business data.
        """
        pass
