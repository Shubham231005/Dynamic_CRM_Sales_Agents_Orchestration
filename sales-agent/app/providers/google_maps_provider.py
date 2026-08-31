from typing import List, Dict, Any
from app.providers.base import BaseLeadProvider
from playwright.sync_api import sync_playwright
import urllib.parse
import asyncio
import logging
import time

logger = logging.getLogger(__name__)

class GoogleMapsProvider(BaseLeadProvider):
    def _do_search(self, industry: str, location: str, max_results: int) -> List[Dict[str, Any]]:
        import sys
        import asyncio
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            # Fix: Manually create and attach the loop for this background thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        query = f"{industry} in {location}"
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.google.com/maps/search/{encoded_query}"
        
        results = []
        
        try:
            with sync_playwright() as p:
                # Turn off headless so the user can see the AI working!
                browser = p.chromium.launch(headless=False)
                page = browser.new_page()
                
                logger.info(f"Navigating to {url}")
                page.goto(url)
                
                # Wait for the main feed to load
                try:
                    page.wait_for_selector('a[href*="/maps/place/"]', timeout=15000)
                except Exception as e:
                    logger.warning(f"Timeout waiting for elements: {e}")
                
                # Let dynamic content load
                time.sleep(3)
                
                # Extract all URLs first
                articles = page.query_selector_all('a[href*="/maps/place/"]')
                place_urls = []
                for article in articles:
                    href = article.get_attribute('href')
                    if href:
                        if not href.startswith('http'):
                            href = "https://www.google.com" + href
                        place_urls.append(href)
                        
                    if len(place_urls) >= max_results:
                        break
                        
                logger.info(f"Found {len(place_urls)} place links. Starting deep scrape...")
                
                # Visit each URL to extract detailed info
                for place_url in place_urls:
                    try:
                        logger.info(f"Scraping detailed place: {place_url}")
                        page.goto(place_url)
                        
                        try:
                            # Wait for the main title to appear
                            page.wait_for_selector('h1', timeout=10000)
                            time.sleep(2) # Give it a moment to load the sidebar info
                        except:
                            pass
                            
                        company_name = ""
                        try:
                            el = page.query_selector('h1')
                            if el:
                                company_name = el.inner_text().strip()
                        except:
                            pass
                            
                        if not company_name:
                            continue
                            
                        phone = None
                        try:
                            phone_el = page.query_selector('button[data-tooltip="Copy phone number"]')
                            if phone_el:
                                aria = phone_el.get_attribute("aria-label")
                                if aria and "Phone:" in aria:
                                    phone = aria.replace("Phone:", "").strip()
                                else:
                                    phone = phone_el.inner_text().strip()
                        except:
                            pass
                            
                        website = None
                        try:
                            web_el = page.query_selector('a[data-tooltip="Open website"]')
                            if web_el:
                                website = web_el.get_attribute("href")
                        except:
                            pass
                            
                        address = None
                        try:
                            addr_el = page.query_selector('button[data-tooltip="Copy address"]')
                            if addr_el:
                                aria = addr_el.get_attribute("aria-label")
                                if aria and "Address:" in aria:
                                    address = aria.replace("Address:", "").strip()
                                else:
                                    address = addr_el.inner_text().strip()
                        except:
                            pass
                            
                        rating = None
                        try:
                            all_spans = page.query_selector_all('span[role="img"]')
                            for span in all_spans:
                                aria = span.get_attribute("aria-label")
                                if aria and "stars" in aria:
                                    # e.g. "4.5 stars"
                                    try:
                                        r_str = aria.split(" ")[0]
                                        rating = float(r_str)
                                    except:
                                        pass
                                    break
                        except:
                            pass
                            
                        results.append({
                            "company_name": company_name,
                            "industry": industry,
                            "location": location,
                            "google_rating": rating,
                            "address": address,
                            "phone": phone,
                            "website": website
                        })
                        
                    except Exception as e:
                        logger.error(f"Error scraping place page: {e}")
                        
                browser.close()
                return results
                
        except Exception as e:
            logger.error(f"Playwright error in GoogleMapsProvider: {e}")
            raise Exception(f"Failed to fetch from Google Maps: {e}")

    async def search_businesses(self, industry: str, location: str, max_results: int) -> List[Dict[str, Any]]:
        # Run the synchronous playwright code in a background thread to bypass Windows asyncio loop issues entirely
        return await asyncio.to_thread(self._do_search, industry, location, max_results)
