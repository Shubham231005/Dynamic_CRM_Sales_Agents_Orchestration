from app.utils.cleaner import (
    normalize_company_name,
    normalize_phone,
    normalize_email,
    normalize_website,
    clean_address
)

def test_normalize_company_name():
    assert normalize_company_name(" ABC Dental Clinic ") == "ABC Dental Clinic"
    assert normalize_company_name("  Multi   Space   Corp ") == "Multi Space Corp"
    assert normalize_company_name("") == ""

def test_normalize_email():
    assert normalize_email(" CONTACT@EXAMPLE.COM ") == "contact@example.com"
    assert normalize_email("Test@test.com") == "test@test.com"
    assert normalize_email("") is None

def test_normalize_phone():
    assert normalize_phone(" +91 98765 43210 ") == "+91 98765 43210"
    assert normalize_phone("") is None

def test_normalize_website():
    assert normalize_website("www.example.com") == "http://www.example.com"
    assert normalize_website("https://example.com") == "https://example.com"
    assert normalize_website("  ") is None

def test_clean_address():
    assert clean_address(" 123   Main St ") == "123 Main St"
    assert clean_address("") is None
