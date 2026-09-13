import hashlib
import httpx
from datetime import datetime, timezone
from typing import Dict, Any

def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

async def fetch_company_comprehensive(org_nr: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    url = f"https://data.brreg.no/enhetsregisteret/api/enheter/{org_nr}"
    roles_url = f"https://data.brreg.no/enhetsregisteret/api/enheter/{org_nr}/roller"
    headers = {"User-Agent": "SignalpostVerifier/2.0"}
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
        "roles": [],
        "evidence": [],
        "changes": []
    }
    
    try:
        resp = await client.get(url, headers=headers, timeout=15.0)
        if resp.status_code == 200:
            data = resp.json()
            c_hash = compute_hash(resp.text)
            
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
            website = None
            website_status = "not_found"
            if raw_site:
                raw_site_clean = raw_site.strip().lower()
                if any(x in raw_site_clean for x in ["facebook.com", "linkedin.com", "instagram.com"]):
                    website_status = "social_link_unverified"
                else:
                    website = raw_site_clean
                    website_status = "registry_provided_unconfirmed"

            profile.update({
                "name": name,
                "status": status,
                "legal_form": legal_form,
                "industry": industry,
                "address": address,
                "employees": employees,
                "website": website,
                "website_status": website_status,
                "confidence": 1.0 if name else 0.0
            })
            
            profile["evidence"].append({
                "field": "basic_attributes",
                "source_url": url,
                "retrieved_at": now_iso,
                "content_hash": c_hash,
                "supporting_text": f"Navn: {name} | Status: {status} | OrgNr: {org_nr} | Form: {legal_form}"
            })
            
            try:
                roles_resp = await client.get(roles_url, headers=headers, timeout=10.0)
                if roles_resp.status_code == 200:
                    r_data = roles_resp.json()
                    r_hash = compute_hash(roles_resp.text)
                    roles_list = []
                    for group in r_data.get("rollegrupper", []):
                        g_type = group.get("type", {}).get("beskrivelse", "Role")
                        for r in group.get("roller", []):
                            p_name = r.get("person", {}).get("navn", {})
                            full_p_name = f"{p_name.get('fornavn', '')} {p_name.get('etternavn', '')}".strip()
                            if full_p_name:
                                roles_list.append(f"{g_type}: {full_p_name}")
                    profile["roles"] = roles_list[:5]
                    profile["evidence"].append({
                        "field": "governance_roles",
                        "source_url": roles_url,
                        "retrieved_at": now_iso,
                        "content_hash": r_hash,
                        "supporting_text": f"Found {len(roles_list)} key personnel/board members."
                    })
            except Exception:
                pass
    except Exception as e:
        profile["evidence"].append({
            "field": "fetch_error",
            "source_url": url,
            "retrieved_at": now_iso,
            "content_hash": "error",
            "supporting_text": str(e)
        })
    return profile
