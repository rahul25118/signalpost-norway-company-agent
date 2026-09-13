import re
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import httpx
from bs4 import BeautifulSoup

def compute_hash_bytes(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()

def extract_literal_snippet(text: str, max_len: int = 300) -> str:
    clean = " ".join(text.split())
    return clean[:max_len]

async def crawl_external_website(raw_url: str, org_name: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    url = raw_url.strip()
    if not url.startswith("http"):
        url = "https://" + url
        
    result = {
        "website_url": url,
        "is_verified": False,
        "description": None,
        "social_links": [],
        "careers_detected": False,
        "evidence_item": None
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SignalpostCrawler/3.0",
        "Accept": "text/html,application/xhtml+xml"
    }
    
    try:
        resp = await client.get(url, headers=headers, timeout=6.0, follow_redirects=True)
        if resp.status_code == 200:
            raw_bytes = resp.content
            c_hash = compute_hash_bytes(raw_bytes)
            soup = BeautifulSoup(raw_bytes, "html.parser")
            
            # 1. Check entity identity in text to verify domain
            page_text = soup.get_text(separator=" ", strip=True)
            norm_org = org_name.lower().split()[0] if org_name else ""
            if norm_org and norm_org in page_text.lower():
                result["is_verified"] = True
                
            # 2. Extract meta description as literal span
            meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
            if meta and meta.get("content"):
                result["description"] = meta.get("content").strip()
            elif page_text:
                result["description"] = extract_literal_snippet(page_text, 250)
                
            # 3. Detect social accounts
            socials = []
            for a in soup.find_all("a", href=True):
                href = a["href"].lower()
                if any(x in href for x in ["linkedin.com/company", "facebook.com", "instagram.com", "twitter.com", "x.com"]):
                    if a["href"] not in socials:
                        socials.append(a["href"])
                if any(term in href for term in ["karriere", "career", "jobb", "stilling", "ledige"]):
                    result["careers_detected"] = True
            result["social_links"] = socials[:4]
            
            # Literal supporting text from actual page bytes
            snippet = result["description"] if result["description"] else extract_literal_snippet(page_text, 200)
            result["evidence_item"] = {
                "field": "company_website_and_activity",
                "source_url": str(resp.url),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "content_hash": c_hash,
                "supporting_text": snippet
            }
    except Exception:
        pass
        
    return result

async def fetch_company_comprehensive(org_nr: str, client: httpx.AsyncClient, previous_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"https://data.brreg.no/enhetsregisteret/api/enheter/{org_nr}"
    roles_url = f"https://data.brreg.no/enhetsregisteret/api/enheter/{org_nr}/roller"
    headers = {"User-Agent": "SignalpostVerifier/3.0 (Evaluation)"}
    now_iso = datetime.now(timezone.utc).isoformat()
    
    profile = {
        "organization_number": org_nr,
        "retrieved_at": now_iso,
        "name": None,
        "legal_form": None,
        "status": "Unknown / Not Found",
        "confidence": 0.0,
        "industry": None,
        "address": None,
        "employees": None,
        "website": None,
        "website_status": "none",
        "description": None,
        "social_accounts": [],
        "hiring_active": False,
        "roles": [],
        "evidence": [],
        "changes": []
    }
    
    try:
        resp = await client.get(url, headers=headers, timeout=12.0)
        if resp.status_code == 200:
            raw_bytes = resp.content
            c_hash = compute_hash_bytes(raw_bytes)
            data = resp.json()
            
            name = data.get("navn")
            is_bankrupt = data.get("konkurs", False)
            is_liquidating = data.get("underAvvikling", False)
            status = "Bankrupt" if is_bankrupt else ("Liquidating" if is_liquidating else "Active")
            legal_form = data.get("organisasjonsform", {}).get("beskrivelse") or data.get("organisasjonsform", {}).get("kode")
            
            naering = data.get("naeringskode1", {})
            industry = f"{naering.get('kode', '')} - {naering.get('beskrivelse', '')}".strip(" - ") or None
            
            addr_obj = data.get("forretningsadresse") or data.get("postadresse") or {}
            addr_parts = addr_obj.get("adresse", [])
            post_place = addr_obj.get("poststed", "")
            post_nr = addr_obj.get("postnummer", "")
            address = f"{', '.join(addr_parts)}, {post_nr} {post_place}".strip(", ") or None
            
            employees = data.get("antallAnsatte")
            raw_site = data.get("hjemmeside")
            
            profile.update({
                "name": name,
                "status": status,
                "legal_form": legal_form,
                "industry": industry,
                "address": address,
                "employees": employees,
                "confidence": 1.0 if name else 0.0
            })
            
            # Literal span directly extracted from the response JSON body
            profile["evidence"].append({
                "field": "basic_attributes",
                "source_url": url,
                "retrieved_at": now_iso,
                "content_hash": c_hash,
                "supporting_text": resp.text[:300]
            })
            
            # Full Roles extraction (no truncation)
            try:
                roles_resp = await client.get(roles_url, headers=headers, timeout=10.0)
                if roles_resp.status_code == 200:
                    r_bytes = roles_resp.content
                    r_hash = compute_hash_bytes(r_bytes)
                    r_data = roles_resp.json()
                    roles_list = []
                    for group in r_data.get("rollegrupper", []):
                        g_type = group.get("type", {}).get("beskrivelse", "Role")
                        for r in group.get("roller", []):
                            p_name = r.get("person", {}).get("navn", {})
                            full_p_name = f"{p_name.get('fornavn', '')} {p_name.get('etternavn', '')}".strip()
                            if full_p_name:
                                roles_list.append(f"{g_type}: {full_p_name}")
                    profile["roles"] = roles_list
                    profile["evidence"].append({
                        "field": "governance_roles",
                        "source_url": roles_url,
                        "retrieved_at": now_iso,
                        "content_hash": r_hash,
                        "supporting_text": roles_resp.text[:300]
                    })
            except Exception:
                pass
                
            # External crawl for website, socials and jobs
            if raw_site:
                ext = await crawl_external_website(raw_site, name, client)
                profile["website"] = ext["website_url"]
                profile["website_status"] = "verified_external" if ext["is_verified"] else "unconfirmed_external"
                profile["description"] = ext["description"]
                profile["social_accounts"] = ext["social_links"]
                profile["hiring_active"] = ext["careers_detected"]
                if ext["evidence_item"]:
                    profile["evidence"].append(ext["evidence_item"])
                    
    except Exception as e:
        profile["evidence"].append({
            "field": "fetch_error",
            "source_url": url,
            "retrieved_at": now_iso,
            "content_hash": "error",
            "supporting_text": str(e)
        })
        
    # Change detection against previous profile
    if previous_profile:
        for key in ["name", "status", "employees", "address", "website"]:
            old_val = previous_profile.get(key)
            new_val = profile.get(key)
            if old_val != new_val and old_val is not None:
                profile["changes"].append({
                    "field": key,
                    "previous": old_val,
                    "current": new_val,
                    "changed_at": now_iso
                })
                
    return profile
