# Signalpost: Autonomous Norwegian Entity Intelligence Agent

An autonomous corporate intelligence and entity verification agent built for the Builderr.ai **Signalpost** challenge. The agent queries official Norwegian business registers (*Brønnøysundregistrene* / *Enhetsregisteret*) to extract, resolve, and audit corporate facts with zero hallucinations and complete evidence provenance.

- **Live Application:** [Streamlit Cloud Demo](https://signalpost-norway-company-agent.streamlit.app)
- **Target Jurisdiction:** Norway (`NO`)
- **Primary Source:** Brønnøysundregistrene Open Data API

---

## 1. ONE-COMMAND RUN

To replicate and run the entire verification pipeline on a dataset:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run agent pipeline on input dataset
PYTHONPATH=src python -m signalpost.cli batch --input data/input/companies_1000.csv --output data/output/profiles_1000.jsonl --concurrency 10
```

To run an interactive audit for a single organization:
```bash
PYTHONPATH=src python -m signalpost.cli single --org-nr 923609016
```

To launch the web interface locally:
```bash
streamlit run app.py
```

---

## 2. COST & RUNTIME METRICS

| Component | Provider / Service | Cost per 1,000 Profiles | Notes |
| :--- | :--- | :--- | :--- |
| **Data Ingestion API** | Enhetsregisteret (Brreg) | **$0.00** | Free public government REST API (no key required) |
| **Entity Resolution** | Local Deterministic / Levenshtein | **$0.00** | Pure CPU heuristics, no external inference calls |
| **Verification Engine** | Rule-based Evidence Auditing | **$0.00** | Zero LLM token consumption |
| **Hosting** | Streamlit Community Cloud | **$0.00** | Free tier deployment |
| **Total Expected Cost** | - | **$0.00** | Fully reproducible at zero cost |

- **Execution Runtime:** ~45-60 seconds for 1,000 profiles (at concurrency=10).
- **External Requests:** Exactly 1 REST query per target entity.

---

## 3. MODEL & ARCHITECTURE SPECIFICATION

- **Design Philosophy:** **Zero Hallucination via Deterministic Extraction.** Financial, legal, and operational corporate data are extracted strictly from authoritative sources. Unverified claims or unregistered entities are explicitly flagged with 0% confidence rather than hallucinated.
- **Entity Resolution Engine:** Strips legal entity forms (`AS`, `ASA`, `ENK`, `DA`) and performs character normalization to verify organization identities against official legal names.
- **Evidence Provenance:** Every exported attribute (`legal_name`, `status`, `address`, `employees`, `industry`) retains source attribution, raw response timestamps, and verification audit trails.

---

## 4. PROJECT STRUCTURE

```text
├── app.py                     # Streamlit live web application
├── requirements.txt           # Python dependencies
├── scripts_validate.py        # Automated submission validation script
├── data/
│   ├── input/
│   │   └── companies_1000.csv # 1,000 target Norwegian company IDs
│   └── output/
│       └── profiles_1000.jsonl# 1,000 validated corporate profiles
├── src/
│   └── signalpost/
│       ├── cli.py             # CLI entrypoint
│       ├── models.py          # Pydantic data schemas
│       ├── budget.py          # Cost & request tracking guards
│       ├── pipeline.py        # Asynchronous orchestrator
│       ├── fetch/             # HTTP client & rate limiting
│       ├── identity/          # Normalization & matching
│       ├── sources/           # Brreg registry adapter
│       └── verification/      # Fact auditing & evidence trails
└── tests/                     # Pytest test suite
```

---

## 5. VALIDATION REPORT SUMMARY

- **Profiles Extracted:** 1,000 / 1,000 (100%)
- **Invalid JSON Lines:** 0
- **Duplicate Records:** 0
- **Missing Source URLs:** 0
- **Integrity Status:** **PASS**
