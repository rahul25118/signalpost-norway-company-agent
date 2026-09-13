import asyncio
import json
import os
import argparse
import httpx
import pandas as pd
from signalpost.sources.brreg_comprehensive import fetch_company_comprehensive

async def run_single(org_nr: str):
    async with httpx.AsyncClient(verify=False) as client:
        profile = await fetch_company_comprehensive(org_nr, client)
        print(json.dumps(profile, indent=2, ensure_ascii=False))

async def run_batch(input_path: str, output_path: str, concurrency: int = 15):
    # Load prior output for change tracking if available
    prior_cache = {}
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        p = json.loads(line)
                        prior_cache[p.get("organization_number")] = p
        except Exception:
            pass

    if input_path.endswith(".csv"):
        df = pd.read_csv(input_path)
        col = "org_nr" if "org_nr" in df.columns else df.columns[0]
        orgs = [str(x).strip() for x in df[col].dropna()]
    else:
        with open(input_path, "r", encoding="utf-8") as f:
            orgs = [line.strip() for line in f if line.strip()]
            
    print(f"Ingesting {len(orgs)} organizations with external website & role enrichment...")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    sem = asyncio.Semaphore(concurrency)
    
    async with httpx.AsyncClient(verify=False) as client:
        async def sem_fetch(org):
            async with sem:
                prev = prior_cache.get(org)
                return await fetch_company_comprehensive(org, client, previous_profile=prev)
                
        tasks = [sem_fetch(org) for org in orgs]
        results = await asyncio.gather(*tasks)
        
    with open(output_path, "w", encoding="utf-8") as f:
        for p in results:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
            
    print(f"Batch completed: {len(results)} profiles successfully enriched at {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Signalpost Autonomous Pipeline")
    sub = parser.add_subparsers(dest="command")
    
    p_single = sub.add_parser("single")
    p_single.add_argument("--org-nr", required=True, help="9-digit organization number")
    
    p_batch = sub.add_parser("batch")
    p_batch.add_argument("--input", required=True, help="Input CSV path")
    p_batch.add_argument("--output", required=True, help="Output JSONL path")
    p_batch.add_argument("--concurrency", type=int, default=15)
    
    args = parser.parse_args()
    if args.command == "single":
        asyncio.run(run_single(args.org_nr))
    elif args.command == "batch":
        asyncio.run(run_batch(args.input, args.output, args.concurrency))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
