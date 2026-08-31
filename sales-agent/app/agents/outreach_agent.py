import logging
import smtplib
from email.message import EmailMessage
from sqlalchemy.orm import Session
from app.database import models
import httpx
import asyncio

try:
    from twilio.rest import Client
    HAS_TWILIO = True
except ImportError:
    HAS_TWILIO = False

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class OutreachAgent:
    def __init__(self, db: Session):
        self.db = db

    async def execute_channel(self, lead_id: int, channel: str) -> str:
        lead = self.db.query(models.Lead).filter(models.Lead.id == lead_id).first()
        if not lead:
            raise ValueError("Lead not found")
            
        settings = self.db.query(models.SalespersonSettings).first()
        if not settings:
            raise ValueError("Salesperson credentials not configured in settings.")
            
        approval = self.db.query(models.ApprovalQueue).filter(
            models.ApprovalQueue.lead_id == lead_id,
            models.ApprovalQueue.action_type == f"SEND_{channel.upper()}"
        ).first()
        
        message_body = approval.proposed_content if approval else None
        
        # If no draft exists, dynamically generate an elite cold outreach draft right now!
        if not message_body or "Draft outreach content" in message_body:
            from app.llm.groq_provider import GroqLLMProvider
            llm = GroqLLMProvider()
            
            # Fetch context from the Strategic Fit if available
            fit = self.db.query(models.StrategicFit).filter(models.StrategicFit.lead_id == lead_id).first()
            strategy = fit.recommended_play.get("strategy") if fit and fit.recommended_play else "Standard Outreach"
            
            prompt = (
                f"You are a top 1% elite salesperson. Write a personalized, highly converting cold {channel} "
                f"message for {lead.company_name} (Industry: {lead.industry}, Location: {lead.location}). "
                f"Strategy: {strategy}. "
                "Keep it punchy, professional, and do not use placeholders like [Your Name]. Just write the message content."
            )
            try:
                message_body = await llm.generate_text(prompt)
                logger.info("Dynamically generated elite draft on the fly.")
            except Exception as e:
                logger.error(f"Failed to dynamically generate draft: {e}")
                message_body = f"Hello {lead.company_name}, we would love to connect."

        channel = channel.lower()
        if channel == "email":
            return await self._send_email(lead, message_body, settings)
        elif channel == "whatsapp":
            return await self._send_whatsapp(lead, message_body, settings)
        elif channel == "call":
            return await self._make_call(lead, message_body, settings)
        elif channel == "telegram":
            return await self._send_telegram(lead, message_body, settings)
        elif channel == "instagram":
            return await self._send_instagram_dm(lead, message_body, settings)
        else:
            raise ValueError(f"Unsupported channel: {channel}")

    async def _send_email(self, lead, message_body, settings):
        if not settings.email_address or not settings.email_password:
            raise ValueError("Email credentials not set.")
            
        target_email = lead.email or lead.business_email
        if not target_email:
            # Fallback for MVP testing: Send it to the salesperson's own email!
            target_email = settings.email_address
            message_body = f"[TEST MODE - LEAD HAS NO EMAIL]\nIntended for: {lead.company_name}\n\n" + message_body
            
        def send_sync():
            msg = EmailMessage()
            msg.set_content(message_body)
            msg['Subject'] = f"Connecting with {lead.company_name}"
            msg['From'] = settings.email_address
            msg['To'] = target_email
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(settings.email_address, settings.email_password)
                smtp.send_message(msg)
                
        await asyncio.to_thread(send_sync)
        return f"Email sent successfully to {target_email}."

    async def _send_whatsapp(self, lead, message_body, settings):
        if not HAS_TWILIO or not settings.twilio_account_sid:
            raise ValueError("Twilio credentials missing or SDK not installed.")
            
        target_phone = lead.phone
        if not target_phone:
            target_phone = settings.phone_number
            message_body = f"[TEST MODE - LEAD HAS NO PHONE]\nIntended for: {lead.company_name}\n\n" + message_body
            
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        target_phone = target_phone if target_phone.startswith("+") else f"+{target_phone}"
        
        message = client.messages.create(
            from_=f"whatsapp:{settings.phone_number}",
            body=message_body,
            to=f"whatsapp:{target_phone}"
        )
        return f"WhatsApp message sent (SID: {message.sid})."

    async def _make_call(self, lead, script, settings):
        if not HAS_TWILIO or not settings.twilio_account_sid:
            raise ValueError("Twilio credentials missing or SDK not installed.")
            
        target_phone = lead.phone
        if not target_phone:
            target_phone = settings.phone_number
            script = f"Test Mode. Lead has no phone. Intended script was: {script}"
            
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        target_phone = target_phone if target_phone.startswith("+") else f"+{target_phone}"
        
        twiml = f"<Response><Say>{script}</Say></Response>"
        call = client.calls.create(
            twiml=twiml,
            to=target_phone,
            from_=settings.phone_number
        )
        return f"AI Call initiated (SID: {call.sid})."

    async def _send_telegram(self, lead, message_body, settings):
        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            raise ValueError("Telegram Bot Token or Chat ID missing.")
            
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": settings.telegram_chat_id,
            "text": f"To {lead.company_name}:\n{message_body}"
        }
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload)
            if res.status_code != 200:
                raise ValueError(f"Telegram API Error: {res.text}")
        return "Telegram message forwarded to Bot successfully."

    async def _send_instagram_dm(self, lead, message_body, settings):
        if not settings.instagram_username or not settings.instagram_password:
            raise ValueError("Instagram credentials not set.")
            
        logger.info(f"Launching Playwright to send Instagram DM to {lead.company_name}...")
        
        target_url = lead.instagram_url
        if not target_url:
            return f"Error: No Instagram URL found for {lead.company_name}. DM could not be sent."
            
        # Extract the exact username from the URL (e.g. https://instagram.com/acmecorp -> acmecorp)
        insta_handle = target_url.strip('/').split('/')[-1]
        
        def run_playwright():
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                # Anti-bot bypass arguments
                browser = p.chromium.launch(
                    headless=False, 
                    args=['--disable-blink-features=AutomationControlled']
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={'width': 1280, 'height': 800}
                )
                page = context.new_page()
                
                # Further mask webdriver
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                try:
                    # 1. Go to the explicit login page first
                    page.goto("https://www.instagram.com/accounts/login/")
                    
                    # 2. Wait for the login form (Handle potential cookie popups)
                    page.wait_for_timeout(3000) # Give the DOM time to settle
                    
                    try:
                        page.get_by_role("button", name="Allow all cookies").click(timeout=2000)
                    except:
                        pass
                        
                    # Try primary selector, fallback to general inputs
                    try:
                        page.wait_for_selector('input[name="username"]', timeout=5000)
                        page.fill('input[name="username"]', settings.instagram_username)
                        page.fill('input[name="password"]', settings.instagram_password)
                        page.press('input[name="password"]', 'Enter')
                    except:
                        logger.warning("Primary IG selectors failed, trying fallback...")
                        page.locator('input[type="text"]').first.fill(settings.instagram_username)
                        pass_input = page.locator('input[type="password"]').first
                        pass_input.fill(settings.instagram_password)
                        pass_input.press('Enter')
                        
                    # 3. Wait for the feed to load (login success)
                    page.wait_for_timeout(8000)
                    
                    # 4. Now navigate directly to the lead's exact DM inbox
                    page.goto(f"https://www.instagram.com/direct/t/{insta_handle}/")
                    page.wait_for_timeout(5000)
                    
                    # 5. Type the personalized message!
                    try:
                        box = page.locator('div[contenteditable="true"]').first
                        box.click(timeout=5000)
                        page.keyboard.type(message_body)
                        page.wait_for_timeout(1000)
                        logger.info("Message typed! Standing by.")
                    except Exception as e:
                        logger.warning(f"Could not type message automatically: {e}")
                    
                    return f"Instagram Playwright Automation Executed! Drafted message to @{insta_handle}."
                except Exception as e:
                    logger.error(f"Insta Error: {e}")
                    raise ValueError(f"Failed to automate Instagram: {str(e)}")
                finally:
                    # Keep browser open for a bit so you can see it
                    page.wait_for_timeout(5000)
                    browser.close()

        # Run synchronously in a background thread to bypass Windows Asyncio Subprocess bugs!
        result = await asyncio.to_thread(run_playwright)
        return result
