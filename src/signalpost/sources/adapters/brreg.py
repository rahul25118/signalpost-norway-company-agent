from typing import Optional, Dict, Any, List
import logging
from signalpost.fetch.http_client import ResilientHttpClient
from signalpost.models import SourceEvidence

logger = logging.getLogger(__name__)

class BrregAdapter:
    """Authoritative API adapter for the Norwegian Central Register (Enhetsregisteret)."""
    BASE_URL = "https://data.brreg.no/enhetsregisteret/api/enheter"

    def __init__(self, http_client: ResilientHttpClient):
        self.client = http_client

    async def fetch_unit(self, org_nr: str) -> Optional[Dict[str, Any]]:
        url = f"{self.BASE_URL}/{org_nr}"
        try:
            resp = await self.client.get(url)
            return resp.json()
        except Exception as e:
            logger.warning(f"[BrregAdapter] Lookup failed for {org_nr}: {str(e)}")
            return None

    def extract_evidence(self, raw_data: Dict[str, Any], org_nr: str) -> List[SourceEvidence]:
        evidences: List[SourceEvidence] = []
        source_url = f"{self.BASE_URL}/{org_nr}"
        now_dt = raw_data.get("registreringsdatoEnhetsregisteret", "N/A")

        if "navn" in raw_data:
            evidences.append(SourceEvidence(
                field="company_name",
                value=raw_data["navn"],
                source_url=source_url,
                source_name="Brønnøysundregistrene (Enhetsregisteret)",
                source_type="registry",
                published_date=now_dt,
                evidence_text=f"Registered name: {raw_data['navn']}",
                company_match=True,
                verification_status="verified"
            ))

        status = "Active"
        if raw_data.get("konkurs", False):
            status = "Bankrupt"
        elif raw_data.get("underAvvikling", False):
            status = "In Liquidation"
        elif raw_data.get("underTvangsavviklingEllerTvangsopplosning", False):
            status = "Under Forced Liquidation"

        evidences.append(SourceEvidence(
            field="legal_status",
            value=status,
            source_url=source_url,
            source_name="Brønnøysundregistrene (Enhetsregisteret)",
            source_type="registry",
            published_date=now_dt,
            evidence_text=f"konkurs={raw_data.get('konkurs')}, underAvvikling={raw_data.get('underAvvikling')}",
            company_match=True,
            verification_status="verified"
        ))

        if "organisasjonsform" in raw_data and "beskrivelse" in raw_data["organisasjonsform"]:
            evidences.append(SourceEvidence(
                field="organization_form",
                value=raw_data["organisasjonsform"]["beskrivelse"],
                source_url=source_url,
                source_name="Brønnøysundregistrene (Enhetsregisteret)",
                source_type="registry",
                published_date=now_dt,
                evidence_text=f"Legal form: {raw_data['organisasjonsform'].get('kode')}",
                company_match=True,
                verification_status="verified"
            ))

        p_addr = raw_data.get("forretningsadresse") or raw_data.get("postadresse")
        if p_addr:
            address_parts = p_addr.get("adresse", [])
            street_address = ", ".join(address_parts) if address_parts else None
            if street_address:
                evidences.append(SourceEvidence(
                    field="address",
                    value=street_address,
                    source_url=source_url,
                    source_name="Brønnøysundregistrene (Enhetsregisteret)",
                    source_type="registry",
                    published_date=now_dt,
                    evidence_text=f"Address: {street_address}",
                    company_match=True,
                    verification_status="verified"
                ))
            if "kommune" in p_addr:
                evidences.append(SourceEvidence(
                    field="municipality",
                    value=p_addr["kommune"],
                    source_url=source_url,
                    source_name="Brønnøysundregistrene (Enhetsregisteret)",
                    source_type="registry",
                    published_date=now_dt,
                    evidence_text=f"Municipality: {p_addr['kommune']}",
                    company_match=True,
                    verification_status="verified"
                ))
            if "postnummer" in p_addr:
                evidences.append(SourceEvidence(
                    field="postal_code",
                    value=str(p_addr["postnummer"]),
                    source_url=source_url,
                    source_name="Brønnøysundregistrene (Enhetsregisteret)",
                    source_type="registry",
                    published_date=now_dt,
                    evidence_text=f"Postal code: {p_addr['postnummer']} {p_addr.get('poststed', '')}",
                    company_match=True,
                    verification_status="verified"
                ))

        if "naeringskode1" in raw_data and "beskrivelse" in raw_data["naeringskode1"]:
            nace = raw_data["naeringskode1"]
            industry_val = f"{nace.get('kode')} - {nace.get('beskrivelse')}"
            evidences.append(SourceEvidence(
                field="industry",
                value=industry_val,
                source_url=source_url,
                source_name="Brønnøysundregistrene (Enhetsregisteret)",
                source_type="registry",
                published_date=now_dt,
                evidence_text=f"NACE: {industry_val}",
                company_match=True,
                verification_status="verified"
            ))

        if "hjemmeside" in raw_data and raw_data["hjemmeside"]:
            evidences.append(SourceEvidence(
                field="website",
                value=raw_data["hjemmeside"],
                source_url=source_url,
                source_name="Brønnøysundregistrene (Enhetsregisteret)",
                source_type="registry",
                published_date=now_dt,
                evidence_text=f"Website: {raw_data['hjemmeside']}",
                company_match=True,
                verification_status="verified"
            ))

        if "antallAnsatte" in raw_data:
            evidences.append(SourceEvidence(
                field="employees",
                value=int(raw_data["antallAnsatte"]),
                source_url=source_url,
                source_name="Brønnøysundregistrene (Enhetsregisteret)",
                source_type="registry",
                published_date=now_dt,
                evidence_text=f"Employees: {raw_data['antallAnsatte']}",
                company_match=True,
                verification_status="verified"
            ))

        return evidences
