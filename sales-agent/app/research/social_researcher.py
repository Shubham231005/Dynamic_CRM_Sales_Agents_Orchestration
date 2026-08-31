import asyncio
from typing import Dict, Any
from playwright.sync_api import sync_playwright
import sys
import logging

logger = logging.getLogger(__name__)

class SocialResearcher:
    def _do_research(self, url: str) -> Dict[str, Any]:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            
        results = {
            "description": None,
            "website_link": None
        }
        
        try:
            with sync_playwright() as p:
                # Turn off headless so the user can see the AI working!
                browser = p.chromium.launch(headless=False)
                page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
                
                try:
                    # We only do a superficial page load. Social networks aggressively block bots.
                    # We just try to grab basic meta tags before JavaScript challenges load.
                    page.goto(url, timeout=10000, wait_until="domcontentloaded")
                    
                    # Try OpenGraph description
                    desc = page.evaluate('document.querySelector("meta[property=\\"og:description\\"]")?.content')
                    if not desc:
                        desc = page.evaluate('document.querySelector("meta[name=\\"description\\"]")?.content')
                        
                    if desc:
                        results["description"] = str(desc).strip()
                        
                except Exception as e:
                    logger.warning(f"SocialResearcher blocked or timeout on {url}: {e}")
                
                browser.close()
        except Exception as e:
            logger.error(f"SocialResearcher error on {url}: {e}")
            
        return results

    async def research(self, profile_url: str) -> Dict[str, Any]:
        """Attempts to superficially grab public info from a social profile."""
        if not profile_url: return {}
        return await asyncio.to_thread(self._do_research, profile_url)
