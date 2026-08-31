import re
from urllib.parse import urlparse

def normalize_company_name(name: str) -> str:
    if not name:
        return ""
    # Remove leading/trailing spaces, replace multiple spaces with single space
    return " ".join(name.strip().split())

def normalize_phone(phone: str) -> str | None:
    if not phone:
        return None
    # Just strip leading/trailing spaces and basic non-printables for now
    cleaned = phone.strip()
    return cleaned if cleaned else None

def normalize_email(email: str) -> str | None:
    if not email:
        return None
    cleaned = email.strip().lower()
    return cleaned if cleaned else None

def normalize_website(url: str) -> str | None:
    if not url:
        return None
    url = url.strip()
    if not url:
        return None
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url
    return url

def clean_address(address: str) -> str | None:
    if not address:
        return None
    cleaned = " ".join(address.strip().split())
    return cleaned if cleaned else None
