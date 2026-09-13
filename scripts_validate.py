import json
import sys

input_path = "data/output/profiles_1000.jsonl"
print(f"Auditing output dataset: {input_path}")

profiles = []
seen_orgs = set()
duplicates = 0
invalid_json = 0
missing_orgs = 0
missing_evidence = 0
missing_urls = 0
zero_confidence = 0

with open(input_path, "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        line = line.strip()
        if not line:
            continue
        try:
            p = json.loads(line)
            profiles.append(p)
        except Exception:
            invalid_json += 1
            continue

        org_nr = p.get("organization_number")
        if not org_nr or len(str(org_nr)) != 9:
            missing_orgs += 1
        elif org_nr in seen_orgs:
            duplicates += 1
        else:
            seen_orgs.add(org_nr)

        evidence = p.get("evidence", [])
        if not evidence:
            missing_evidence += 1
        else:
            for ev in evidence:
                if not ev.get("source_url"):
                    missing_urls += 1

        if p.get("confidence", 0) == 0:
            zero_confidence += 1

total_count = len(profiles)

sep = "=" * 50
print(sep)
print("             FINAL_VALIDATION_REPORT             ")
print(sep)
status_count = "PASS" if total_count >= 1000 else "FAIL"
status_json = "PASS" if invalid_json == 0 else "FAIL"
status_dups = "PASS" if duplicates == 0 else "FAIL"
status_orgs = "PASS" if missing_orgs == 0 else "FAIL"
status_ev = "PASS" if missing_evidence == 0 else "FAIL"
status_urls = "PASS" if missing_urls == 0 else "FAIL"

print(f"Total Profiles Count:      {total_count:<6} [{status_count}]")
print(f"Invalid JSON Lines:        {invalid_json:<6} [{status_json}]")
print(f"Duplicate Org Numbers:     {duplicates:<6} [{status_dups}]")
print(f"Missing / Bad Org Numbers: {missing_orgs:<6} [{status_orgs}]")
print(f"Profiles Lacking Evidence: {missing_evidence:<6} [{status_ev}]")
print(f"Evidence Missing Source:   {missing_urls:<6} [{status_urls}]")
print(f"Zero-Confidence Entities:  {zero_confidence:<6} [INFO]")
print(sep)

all_passed = all(s == "PASS" for s in [status_count, status_json, status_dups, status_orgs, status_ev, status_urls])
if all_passed:
    print("STATUS: DATASET INTEGRITY FULLY VERIFIED (READY FOR SUBMISSION)")
else:
    print("STATUS: VALIDATION CHECKS FAILED - RESOLUTION REQUIRED")
    sys.exit(1)
