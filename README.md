# Signalpost: Autonomous Norwegian Entity Intelligence Agent (v2.0)

An autonomous corporate intelligence and entity verification agent built for the Builderr.ai **Signalpost** challenge. The agent queries official Norwegian business registers (*Brønnøysundregistrene* / *Enhetsregisteret*) to extract, resolve, and audit corporate facts, governance roles, and operational status with complete cryptographic evidence provenance.

- **Live Application:** [Streamlit Cloud Demo](https://signalpost-norway-company-agent.streamlit.app)
- **Target Jurisdiction:** Norway (`NO`)
- **Primary Source:** Brønnøysundregistrene Central Register API (Enhetsregisteret & Roller)

---

## 1. RUN INSTRUCTIONS

### Single Organization Lookup:
```bash
PYTHONPATH=src python -m signalpost.cli single --org-nr 810034882
