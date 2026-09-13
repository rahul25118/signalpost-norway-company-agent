import json
import sys

input_path = "data/output/profiles_1000.jsonl"
print(f"Auditing refreshed dataset: {input_path}")

profiles = []
seen_orgs = set()
duplicates = 0
invalid_json = 0
missing_evidence = 0
missing_hashes = 0
missing_roles = 0

with open(input_path, "r", encoding="utf-8") as f:
    for line in f:
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
        if org_nr in seen_orgs:
            duplicates += 1
        else:
            seen_orgs.add(org_nr)

        evidence = p.get("evidence", [])
        if not evidence:
            missing_evidence += 1
        else:
            for ev in evidence:
                if not ev.get("content_hash"):
                    missing_hashes += 1

        if p.get("roles"):
            missing_roles += 1

total = len(profiles)
print("=" * 50)
print(f"Total Profiles:          {total} [{'PASS' if total == 1000 else 'FAIL'}]")
print(f"Invalid JSON Lines:      {invalid_json} [{'PASS' if invalid_json == 0 else 'FAIL'}]")
print(f"Duplicates:              {duplicates} [{'PASS' if duplicates == 0 else 'FAIL'}]")
print(f"Missing Evidence:        {missing_evidence} [{'PASS' if missing_evidence == 0 else 'FAIL'}]")
print(f"Missing Content Hashes:  {missing_hashes} [{'PASS' if missing_hashes == 0 else 'FAIL'}]")
print(f"Companies With Roles:    {missing_roles} (Info)")
print("=" * 50)
