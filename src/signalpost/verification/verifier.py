from typing import List, Dict, Any, Tuple
from collections import defaultdict
from signalpost.models import SourceEvidence, FactConflict

SOURCE_TRUST_HIERARCHY = {
    "registry": 1.0,
    "corporate_site": 0.8,
    "web_directory": 0.6,
    "unverified": 0.2
}

class VerificationEngine:
    @staticmethod
    def audit_and_consolidate(
        evidences: List[SourceEvidence]
    ) -> Tuple[Dict[str, Any], List[FactConflict], float]:
        field_groups: Dict[str, List[SourceEvidence]] = defaultdict(list)
        for ev in evidences:
            if ev.company_match and ev.verification_status == "verified":
                field_groups[ev.field].append(ev)

        consolidated: Dict[str, Any] = {}
        conflicts: List[FactConflict] = []
        field_confidences: List[float] = []

        for field, ev_list in field_groups.items():
            unique_values = {}
            for ev in ev_list:
                val_key = str(ev.value).strip().lower()
                if val_key not in unique_values:
                    unique_values[val_key] = []
                unique_values[val_key].append(ev)

            if len(unique_values) == 1:
                best_ev = ev_list[0]
                consolidated[field] = best_ev.value
                trust = SOURCE_TRUST_HIERARCHY.get(best_ev.source_type, 0.5)
                field_confidences.append(trust)
            else:
                sorted_by_trust = sorted(
                    ev_list, 
                    key=lambda x: SOURCE_TRUST_HIERARCHY.get(x.source_type, 0.0), 
                    reverse=True
                )
                top_ev = sorted_by_trust[0]
                second_ev = sorted_by_trust[1]
                
                top_trust = SOURCE_TRUST_HIERARCHY.get(top_ev.source_type, 0.0)
                second_trust = SOURCE_TRUST_HIERARCHY.get(second_ev.source_type, 0.0)

                if top_trust > second_trust:
                    consolidated[field] = top_ev.value
                    conflicts.append(FactConflict(
                        field=field,
                        source_a=top_ev.source_name,
                        value_a=top_ev.value,
                        source_b=second_ev.source_name,
                        value_b=second_ev.value,
                        resolution=f"Selected {top_ev.source_type} over {second_ev.source_type} based on governance hierarchy",
                        explanation=f"Resolved conflict: prioritised authoritative {top_ev.source_type}."
                    ))
                    field_confidences.append(top_trust * 0.9)
                else:
                    conflicts.append(FactConflict(
                        field=field,
                        source_a=top_ev.source_name,
                        value_a=top_ev.value,
                        source_b=second_ev.source_name,
                        value_b=second_ev.value,
                        resolution=None,
                        explanation="Unresolved discrepancy between equally-weighted sources. Withheld from primary record."
                    ))
                    field_confidences.append(0.2)

        overall_confidence = (
            sum(field_confidences) / len(field_confidences) if field_confidences else 0.0
        )
        return consolidated, conflicts, round(overall_confidence, 2)
