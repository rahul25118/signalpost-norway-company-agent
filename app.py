import streamlit as st
import asyncio
import pandas as pd
import json
from signalpost.budget import ExecutionBudgetTracker
from signalpost.pipeline import ResearchPipeline

st.set_page_config(page_title="Signalpost Agent", page_icon="🔍", layout="wide")

st.title("🇳🇴 Signalpost: Norwegian Company Intelligence Agent")
st.markdown("Autonomous research agent extracting authoritative company data from official Norwegian registers with zero hallucinations.")

tab1, tab2 = st.tabs(["Single Company Lookup", "Batch Processing"])

with tab1:
    org_input = st.text_input("Enter 9-digit Norwegian Org Number:", value="923609016")
    if st.button("Research Entity", type="primary"):
        with st.spinner("Querying Enhetsregisteret & compiling evidence..."):
            async def run_single():
                tracker = ExecutionBudgetTracker(max_requests=20, max_cost_usd=0.1)
                pipeline = ResearchPipeline(tracker, user_agent="SignalpostWeb/1.0")
                try:
                    return await pipeline.research_company(org_input.strip())
                finally:
                    await pipeline.close()

            profile = asyncio.run(run_single())
            
            st.success(f"Verified: {profile.company_name or 'Not Found'}")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Status", profile.legal_status)
            col2.metric("Confidence", f"{profile.confidence * 100:.0f}%")
            col3.metric("Latency", f"{profile.processing_metadata.execution_time_seconds:.2f}s")
            
            st.subheader("Extracted Attributes")
            details = {
                "Org Number": profile.organization_number,
                "Legal Form": profile.organization_form,
                "Industry": profile.industry,
                "Address": f"{profile.address}, {profile.postal_code} {profile.municipality}",
                "Employees": profile.employees,
                "Website": profile.website
            }
            st.json(details)
            
            with st.expander("Audit Trail & Evidence (Traceability)"):
                st.write(profile.evidence)

with tab2:
    st.markdown("Upload a CSV with an `org_nr` column to run concurrent batch processing.")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file and st.button("Run Batch"):
        df = pd.read_csv(uploaded_file)
        orgs = [str(x).strip() for x in df.iloc[:, 0].tolist() if str(x).strip().isdigit()]
        
        st.info(f"Processing {len(orgs)} organizations...")
        
        async def run_batch():
            tracker = ExecutionBudgetTracker(max_requests=500, max_cost_usd=1.0)
            pipeline = ResearchPipeline(tracker, user_agent="SignalpostBatch/1.0")
            sem = asyncio.Semaphore(5)
            
            async def worker(o):
                async with sem:
                    return await pipeline.research_company(o)
            
            try:
                tasks = [worker(o) for o in orgs]
                return await asyncio.gather(*tasks)
            finally:
                await pipeline.close()
                
        results = asyncio.run(run_batch())
        records = [
            {
                "Org Nr": r.organization_number,
                "Name": r.company_name,
                "Status": r.legal_status,
                "Confidence": r.confidence,
                "Employees": r.employees
            }
            for r in results
        ]
        st.dataframe(pd.DataFrame(records))
