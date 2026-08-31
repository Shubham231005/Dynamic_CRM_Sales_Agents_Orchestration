import asyncio
from app.research.providers.playwright_search import PlaywrightSearchProvider
import logging

logging.basicConfig(level=logging.DEBUG)

async def test_search():
    provider = PlaywrightSearchProvider()
    print("Running search for 'BonBon Supermarket Andheri'")
    results = await provider.search("BonBon Supermarket Andheri", max_results=5)
    print("RESULTS:")
    print(results)

if __name__ == "__main__":
    asyncio.run(test_search())
