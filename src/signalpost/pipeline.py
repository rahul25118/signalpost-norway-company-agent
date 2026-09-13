import time
import logging
from typing import Optional, List
from signalpost.models import CompanyProfile, ProcessingMetadata, SourceEvidence
from signalpost.budget import ExecutionBudgetTracker
from signalpost.fetch.http_client import ResilientHttpClient
from signalpost.sources.adapters.brreg import BrregAdapter
from signalpost.verification.verifier import VerificationEngine

logger = logging.getLogger(__name__)

class ResearchPipeline:
    def __init__(self, budget_tracker: ExecutionBudgetTracker, user_agent: str):
        self.budget_tracker = budget_tracker
        self.http_client = ResilientHttpClient(budget_tracker, user_agent=user_agent)
        self.brreg = BrregAdapter(self.http_client)

    async def research_company(self, organization_number: str) -> CompanyProfile:
        start_time = time.perf_counter()
        req_counter_start = (await self.budget_tracker.snapshot())["requests_used"]
        adapters_queried: List[str] = []
        all_evidences: List[SourceEvidence] = []

        adapters_queried.append("Brønnøysundregistrene")
        brreg_payload = await self.brreg.fetch_unit(organization_number)

        if not brreg_payload:
            duration = time.perf_counter() - start_time
            return CompanyProfile(
                organization_number=organization_number,
                legal_status="Unknown / Not Found in Central Register",
                confidence=0.0,
                processing_metadata=ProcessingMetadata(
                    execution_time_seconds=round(duration, 3),
                    total_http_requests=1,
                    adapters_queried=adapters_queried
                )
            )

        brreg_evidences = self.brreg.extract_evidence(brreg_payload, organization_number)
        all_evidences.extend(brreg_evidences)

        consolidated, conflicts, confidence = VerificationEngine.audit_and_consolidate(all_evidences)

        unique_sources = list({ev.source_url for ev in all_evidences if ev.source_url})
        important_facts = [
            f"Registered under organization form: {consolidated.get('organization_form', 'N/A')}",
            f"Operational status verified as {consolidated.get('legal_status', 'Unknown')}."
        ]

        req_counter_end = (await self.budget_tracker.snapshot())["requests_used"]
        duration = time.perf_counter() - start_time

        return CompanyProfile(
            organization_number=organization_number,
            company_name=consolidated.get("company_name"),
            legal_status=consolidated.get("legal_status"),
            organization_form=consolidated.get("organization_form"),
            address=consolidated.get("address"),
            municipality=consolidated.get("municipality"),
            postal_code=consolidated.get("postal_code"),
            website=consolidated.get("website"),
            industry=consolidated.get("industry"),
            employees=consolidated.get("employees"),
            financial_facts={},
            important_company_facts=important_facts,
            sources=unique_sources,
            evidence=all_evidences,
            conflicts=conflicts,
            confidence=confidence,
            processing_metadata=ProcessingMetadata(
                execution_time_seconds=round(duration, 3),
                total_http_requests=req_counter_end - req_counter_start,
                adapters_queried=adapters_queried
            )
        )

    async def close(self):
        await self.http_client.aclose()
