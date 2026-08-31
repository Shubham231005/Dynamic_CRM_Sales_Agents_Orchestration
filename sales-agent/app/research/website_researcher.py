import asyncio
import re
from typing import Dict, Any, List
from playwright.sync_api import sync_playwright
import urllib.parse
import sys
import logging

logger = logging.getLogger(__name__)

class WebsiteResearcher:
    MAX_PAGES = 8
    
    def _get_links_to_crawl(self, base_url: str, page) -> List[str]:
        target_paths = [
            "/about", "/about-us", "/services", "/products", 
            "/contact", "/contact-us", "/team", "/our-team", 
            "/classes", "/locations"
        ]
        
        links_to_crawl = [base_url]
        try:
            hrefs = page.evaluate("Array.from(document.querySelectorAll('a')).map(a => a.href)")
            for href in hrefs:
                if not href or not href.startswith("http"): continue
                
                # Check if it's same domain
                if urllib.parse.urlparse(base_url).netloc not in href: continue
                
                path = urllib.parse.urlparse(href).path.lower()
                # Strip trailing slash for matching
                if path.endswith('/'): path = path[:-1]
                
                if path in target_paths and href not in links_to_crawl:
                    links_to_crawl.append(href)
                    
                if len(links_to_crawl) >= self.MAX_PAGES:
                    break
        except Exception as e:
            logger.warning(f"Error extracting links: {e}")
            
        return links_to_crawl[:self.MAX_PAGES]

    def _do_crawl(self, official_url: str) -> Dict[str, Any]:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            
        results = {
            "emails": set(),
            "phones": set(),
            "social_links": set(),
            "whatsapp_urls": set(),
            "description": None,
            "services": set(),
            "products": set()
        }
        
        try:
            with sync_playwright() as p:
                # Turn off headless so the user can see the AI working!
                browser = p.chromium.launch(headless=False)
                context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
                page = context.new_page()
                
                try:
                    page.goto(official_url, timeout=15000, wait_until="domcontentloaded")
                except:
                    browser.close()
                    return results
                
                # 1. Grab subpages
                pages_to_crawl = self._get_links_to_crawl(official_url, page)
                logger.info(f"WebsiteResearcher will crawl {len(pages_to_crawl)} pages on {official_url}")
                
                for url in pages_to_crawl:
                    try:
                        if url != official_url: # Skip re-navigating to homepage if already there
                            page.goto(url, timeout=10000, wait_until="domcontentloaded")
                            
                        # Extract description if on homepage or about
                        if url == official_url or "about" in url.lower():
                            if not results["description"]:
                                desc = page.evaluate('document.querySelector("meta[name=\\"description\\"]")?.content')
                                if desc: results["description"] = str(desc).strip()
                                
                        # Extract basic factual lists (Services/Products)
                        path = urllib.parse.urlparse(url).path.lower()
                        if "service" in path or "class" in path:
                            # Basic heuristic: grab H2s or list items
                            items = page.evaluate("Array.from(document.querySelectorAll('h2, h3, li')).map(el => el.innerText).filter(t => t.length > 3 && t.length < 50)")
                            for item in items: results["services"].add(item.strip())
                        elif "product" in path:
                            items = page.evaluate("Array.from(document.querySelectorAll('h2, h3, li')).map(el => el.innerText).filter(t => t.length > 3 && t.length < 50)")
                            for item in items: results["products"].add(item.strip())
                            
                        # Extract Links (Social, WhatsApp, Email, Phone)
                        hrefs = page.evaluate("Array.from(document.querySelectorAll('a')).map(a => a.href)")
                        for href in hrefs:
                            if not href: continue
                            hl = href.lower()
                            if hl.startswith("mailto:"):
                                results["emails"].add(hl.replace("mailto:", "").split("?")[0].strip())
                            elif hl.startswith("tel:"):
                                results["phones"].add(hl.replace("tel:", "").strip())
                            elif "api.whatsapp.com" in hl or "wa.me/" in hl:
                                results["whatsapp_urls"].add(href)
                            elif any(domain in hl for domain in ["instagram.com/", "facebook.com/", "linkedin.com/company/", "youtube.com/"]):
                                results["social_links"].add(href)
                                
                        # Regex on body text for emails
                        body_text = page.inner_text("body")
                        found_emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", body_text)
                        for em in found_emails:
                            if not em.endswith(('png', 'jpg', 'jpeg')):
                                results["emails"].add(em.lower())
                                
                    except Exception as e:
                        logger.warning(f"Error crawling subpage {url}: {e}")
                        
                browser.close()
        except Exception as e:
            logger.error(f"WebsiteResearcher error on {official_url}: {e}")
            
        # Convert sets to lists
        return {k: list(v) if isinstance(v, set) else v for k, v in results.items()}

    async def research(self, official_url: str) -> Dict[str, Any]:
        """Crawls a verified website to extract factual contact and company info."""
        if not official_url: return {}
        if not official_url.startswith("http"): official_url = "https://" + official_url
        return await asyncio.to_thread(self._do_crawl, official_url)
