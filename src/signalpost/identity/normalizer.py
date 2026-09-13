import re
import unicodedata
from typing import Optional

NORWEGIAN_SUFFIXES = [
    r"\basa\b", r"\bas\b", r"\bda\b", r"\bans\b", r"\benk\b", 
    r"\bks\b", r"\bba\b", r"\bsa\b", r"\bholding\b", r"\bgruppen\b", r"\bgroup\b"
]

def clean_org_number(raw_org: str) -> Optional[str]:
    cleaned = re.sub(r"\D", "", str(raw_org).strip())
    if len(cleaned) == 9 and cleaned.isdigit():
        return cleaned
    return None

def normalize_company_name(name: str) -> str:
    if not name:
        return ""
    norm = unicodedata.normalize("NFKD", name).lower()
    norm = re.sub(r"[^\w\s]", " ", norm)
    
    for suffix in NORWEGIAN_SUFFIXES:
        norm = re.sub(suffix, "", norm)
        
    norm = re.sub(r"\s+", " ", norm).strip()
    return norm
