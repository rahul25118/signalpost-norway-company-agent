from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class SourceEvidence(BaseModel):
    field: str
    value: Any
    source_url: str
    source_name: str
    source_type: str  # registry | corporate_site | web_directory
    published_date: Optional[str] = None
    retrieved_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    evidence_text: str
    company_match: bool = True
    verification_status: str = "verified"

class FactConflict(BaseModel):
    field: str
    source_a: str
    value_a: Any
    source_b: str
    value_b: Any
    resolution: Optional[str] = None
    explanation: str

class ProcessingMetadata(BaseModel):
    execution_time_seconds: float
    total_http_requests: int
    estimated_cost_usd: float = 0.0
    adapters_queried: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

class CompanyProfile(BaseModel):
    organization_number: str
    company_name: Optional[str] = None
    legal_status: Optional[str] = None
    organization_form: Optional[str] = None
    address: Optional[str] = None
    municipality: Optional[str] = None
    postal_code: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    employees: Optional[int] = None
    financial_facts: Dict[str, Any] = Field(default_factory=dict)
    important_company_facts: List[str] = Field(default_factory=list)
    last_verified: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    sources: List[str] = Field(default_factory=list)
    evidence: List[SourceEvidence] = Field(default_factory=list)
    conflicts: List[FactConflict] = Field(default_factory=list)
    confidence: float = 0.0
    processing_metadata: Optional[ProcessingMetadata] = None

print("models.py created successfully!")
