import re
import hashlib
import base64
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import httpx
from bs4 import BeautifulSoup

def compute_hash_bytes(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()

def extract_literal_snippet(text: str, max_len: int = 300) -> str:
    clean = " ".join(text.split())
    return clean[:max_len]

def is_strict_exact_match(page_text: str, org_nr: str, full_name: str) -> bool:
    org_clean = org_nr.strip()
    formatted_org = f"{org_clean[:3]} {org_clean[3:6]} {org_clean[6:]}"
    if org_clean in page_text or formatted_org in page_text:
        return True
        
    norm_page = page_text.lower()
    norm_name = full_name.lower().strip()
    for suffix in [" as", " asa", " ba", " sa", " da", " ans", " enk"]:
        if norm_name.endswith(suffix):
            norm_name = norm_name[:-len(suffix)].strip()
            break
            
    if len(norm_name) >= 6:
        pattern = r'\b' + re.escape(norm_name) + r'\b'
        if re.search(pattern, norm_page):
            if "kraftverk" in full_name.lower() and "kraftverk" not in norm_page:
                return False
            return True
            
    return False

async def crawl_external_website(raw_url: str, org_nr: str, org_name: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    url = raw_url.strip()
    if not url.startswith("http"):
        url = "https://" + url
        
    result = {
        "website_url": url,
        "is_verified": False,
        "status_label": "unconfirmed_external",
        "description": None,
        "social_links": [],
        "careers_detected": False,
        "evidence_item": None,
        "error": None
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SignalpostCrawler/4.0",
        "Accept": "text/html,application/xhtml+xml"
    }
    
    try:
        resp = await client.get(url, headers=headers, timeout=8.0, follow_redirects=True)
        if resp.status_code == 200:
            raw_bytes = resp.content
            c_hash = compute_hash_bytes(raw_bytes)
            soup = BeautifulSoup(raw_bytes, "html.parser")
            page_text = soup.get_text(separator=" ", strip=True)
            
            if is_strict_exact_match(page_text, org_nr, org_name):
                result["is_verified"] = True
                result["status_label"] = "verified_exact_legal_entity"
                
                meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
                if meta and meta.get("content"):
                    result["description"] = meta.get("content").strip()
                else:
                    result["description"] = extract_literal_snippet(page_text, 250)
                    
                socials = []
                for a in soup.find_all("a", href=True):
                    href = a["href"].lower()
                    if any(x in href for x in ["linkedin.com/company", "facebook.com", "instagram.com"]):
                        if a["href"] not in socials:
                            socials.append(a["href"])
                    if any(term in href for term in ["karriere", "career", "jobb", "stilling", "ledige"]):
                        result["careers_detected"] = True
                result["social_links"] = socials[:4]
                
                snippet = result["description"] if result["description"] else extract_literal_snippet(page_text, 200)
                result["evidence_item"] = {
                    "field": "company_website_and_activity",
                    "source_url": str(resp.url),
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "content_hash": c_hash,
                    "supporting_text": snippet,
                    "raw_snapshot_snippet": base64.b64encode(raw_bytes[:1000]).decode("ascii")
                }
            else:
                result["status_label"] = "unconfirmed_related_or_group"
        else:
            result["error"] = f"HTTP {resp.status_code}"
            result["status_label"] = "fetch_failed"
    except Exception as e:
        result["error"] = str(e)
        result["status_label"] = "connection_failed"
        
    return result

async def fetch_company_comprehensive(org_nr: str, client: httpx.AsyncClient, previous_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"https://data.brreg.no/enhetsregisteret/api/enheter/{org_nr}"
    roles_url = f"https://data.brreg.no/enhetsregisteret/api/enheter/{org_nr}/roller"
    headers = {"User-Agent": "SignalpostVerifier/4.0 (Evaluation)"}
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
        "organization_roles": [],
        "evidence": [],
        "changes": [],
        "errors": []
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
            
            profile["evidence"].append({
                "field": "basic_attributes",
                "source_url": url,
                "retrieved_at": now_iso,
                "content_hash": c_hash,
                "supporting_text": resp.text[:300],
                "raw_snapshot_snippet": base64.b64encode(raw_bytes[:500]).decode("ascii")
            })
            
            try:
                roles_resp = await client.get(roles_url, headers=headers, timeout=10.0)
                if roles_resp.status_code == 200:
                    r_bytes = roles_resp.content
                    r_hash = compute_hash_bytes(r_bytes)
                    r_data = roles_resp.json()
                    person_roles = []
                    org_roles = []
                    
                    for group in r_data.get("rollegrupper", []):
                        g_type = group.get("type", {}).get("beskrivelse", "Role")
                        for r in group.get("roller", []):
                            r_specific = r.get("type", {}).get("beskrivelse") or g_type
                            if r.get("person"):
                                p_name = r.get("person", {}).get("navn", {})
                                full_p_name = f"{p_name.get('fornavn', '')} {p_name.get('etternavn', '')}".strip()
                                if full_p_name:
                                    person_roles.append(f"{r_specific}: {full_p_name}")
                            elif r.get("enhet"):
                                e_name = r.get("enhet", {}).get("navn", "")
                                e_org = r.get("enhet", {}).get("organisasjonsnummer", "")
                                if e_name:
                                    org_roles.append(f"{r_specific}: {e_name} ({e_org})")
                                    
                    profile["roles"] = person_roles
                    profile["organization_roles"] = org_roles
                    profile["evidence"].append({
                        "field": "governance_roles",
                        "source_url": roles_url,
                        "retrieved_at": now_iso,
                        "content_hash": r_hash,
                        "supporting_text": roles_resp.text[:300],
                        "raw_snapshot_snippet": base64.b64encode(r_bytes[:500]).decode("ascii")
                    })
                elif roles_resp.status_code != 404:
                    profile["errors"].append({"source": roles_url, "status": roles_resp.status_code})
            except Exception as e_roles:
                profile["errors"].append({"source": roles_url, "error": str(e_roles)})
                
            if raw_site:
                ext = await crawl_external_website(raw_site, org_nr, name, client)
                profile["website"] = ext["website_url"]
                profile["website_status"] = ext["status_label"]
                if ext["is_verified"]:
                    profile["description"] = ext["description"]
                    profile["social_accounts"] = ext["social_links"]
                    profile["hiring_active"] = ext["careers_detected"]
                    if ext["evidence_item"]:
                        profile["evidence"].append(ext["evidence_item"])
                else:
                    profile["description"] = None
                    profile["social_accounts"] = []
                    profile["hiring_active"] = False
                if ext.get("error"):
                    profile["errors"].append({"source": ext["website_url"], "error": ext["error"]})
        else:
            profile["errors"].append({"source": url, "status": resp.status_code})
            
    except Exception as e:
        profile["errors"].append({"source": url, "error": str(e)})
        profile["evidence"].append({
            "field": "fetch_error",
            "source_url": url,
            "retrieved_at": now_iso,
            "content_hash": "error",
            "supporting_text": str(e)
        })
        
    if previous_profile:
        for key in ["name", "status", "employees", "address", "website", "website_status"]:
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
