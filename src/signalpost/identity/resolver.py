from difflib import SequenceMatcher
from typing import Tuple, Optional
from signalpost.identity.normalizer import clean_org_number, normalize_company_name

class EntityResolver:
    @staticmethod
    def match_organization_number(candidate: str, canonical: str) -> bool:
        c_clean = clean_org_number(candidate)
        can_clean = clean_org_number(canonical)
        return bool(c_clean and can_clean and c_clean == can_clean)

    @staticmethod
    def calculate_name_similarity(name_a: str, name_b: str) -> float:
        norm_a = normalize_company_name(name_a)
        norm_b = normalize_company_name(name_b)
        if not norm_a or not norm_b:
            return 0.0
        if norm_a == norm_b:
            return 1.0
        return SequenceMatcher(None, norm_a, norm_b).ratio()

    @classmethod
    def resolve(
        cls, 
        candidate_org: Optional[str], 
        candidate_name: Optional[str], 
        target_org: str, 
        target_name: str
    ) -> Tuple[bool, float, str]:
        # Level 1: Strict Org Number
        if candidate_org:
            clean_c = clean_org_number(candidate_org)
            if clean_c == target_org:
                return True, 1.0, "Exact organization number matched"
            elif clean_c and clean_c != target_org:
                return False, 0.0, f"Organization number conflict: {clean_c} != {target_org}"

        # Level 2 & 3: Legal Name Matching
        if candidate_name and target_name:
            sim = cls.calculate_name_similarity(candidate_name, target_name)
            if sim >= 0.85:
                return True, sim, f"High name similarity match: {sim:.2f}"
            if sim < 0.60:
                return False, sim, f"Name mismatch score too low: {sim:.2f}"
            return False, sim, f"Ambiguous name similarity: {sim:.2f}"

        return False, 0.0, "Insufficient identity markers to confirm match"
