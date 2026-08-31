import asyncio
import urllib.parse
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright
import sys
import logging
from app.research.providers.base_search import BaseSearchProvider

logger = logging.getLogger(__name__)

class PlaywrightSearchProvider(BaseSearchProvider):
    def _do_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.bing.com/search?q={encoded_query}"
        
        results = []
        try:
            with sync_playwright() as p:
                # Turn off headless so the user can see the AI working!
                browser = p.chromium.launch(headless=False)
                page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                page.goto(url, wait_until="domcontentloaded")
                
                # Bing selectors
                elements = page.query_selector_all('li.b_algo')
                for el in elements:
                    if len(results) >= max_results:
                        break
                        
                    title_el = el.query_selector('h2 a')
                    snippet_el = el.query_selector('.b_caption p, .b_algoSlug')
                    
                    if title_el:
                        href = title_el.get_attribute("href")
                        if not href or not href.startswith("http"):
                            continue
                                
                        title = title_el.inner_text().strip()
                        snippet = snippet_el.inner_text().strip() if snippet_el else ""
                        
                        results.append({
                            "url": href,
                            "title": title,
                            "snippet": snippet,
                            "source_type": "web_search"
                        })
                browser.close()
        except Exception as e:
            logger.error(f"PlaywrightSearchProvider error: {e}")
            
        return results

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._do_search, query, max_results)
