import asyncio
import json
import os
import sys
import click
from rich.console import Console
from signalpost.budget import ExecutionBudgetTracker
from signalpost.pipeline import ResearchPipeline
from signalpost.models import CompanyProfile

console = Console()

@click.group()
def main():
    """Signalpost Autonomous Company Intelligence Agent CLI"""
    pass

@main.command()
@click.option("--company-number", "-c", required=True, help="9-digit Norwegian Organization Number")
def run(company_number: str):
    """Run interactive extraction for a single organization number."""
    async def _execute():
        budget = ExecutionBudgetTracker(max_requests=20, max_cost_usd=0.10)
        pipeline = ResearchPipeline(budget, user_agent="SignalpostBot/1.0")
        try:
            profile = await pipeline.research_company(company_number)
            console.print_json(profile.model_dump_json(indent=2))
        finally:
            await pipeline.close()

    asyncio.run(_execute())

@main.command()
@click.option("--input", "-i", "input_file", required=True, help="Input CSV file containing organization numbers")
@click.option("--output", "-o", "output_file", required=True, help="Destination JSONL path")
@click.option("--concurrency", default=10, help="Concurrent async research tasks")
def batch(input_file: str, output_file: str, concurrency: int):
    """Execute high-throughput batch research."""
    async def _execute_batch():
        if not os.path.exists(input_file):
            console.print(f"[red]Input file {input_file} does not exist.[/red]")
            sys.exit(1)

        with open(input_file, "r", encoding="utf-8") as f:
            lines = [line.strip().split(",")[0] for line in f if line.strip()]
        
        org_numbers = [num for num in lines if num.isdigit() and len(num) == 9]
        console.print(f"[green]Loaded {len(org_numbers)} target companies for processing.[/green]")

        budget = ExecutionBudgetTracker(max_requests=2000, max_cost_usd=10.0)
        pipeline = ResearchPipeline(budget, user_agent="SignalpostBot/1.0")
        sem = asyncio.Semaphore(concurrency)

        output_dir = os.path.dirname(os.path.abspath(output_file))
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        async def worker(org_nr: str):
            async with sem:
                return await pipeline.research_company(org_nr)

        try:
            tasks = [worker(org) for org in org_numbers]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            written = 0
            with open(output_file, "w", encoding="utf-8") as out:
                for res in results:
                    if isinstance(res, CompanyProfile):
                        out.write(res.model_dump_json() + "\n")
                        written += 1
            
            console.print(f"[bold green]Successfully generated {written} profiles in {output_file}[/bold green]")
        finally:
            await pipeline.close()

    asyncio.run(_execute_batch())

if __name__ == "__main__":
    main()
