"""
Command Line Interface (CLI) for FrontierAtlas Intelligence Graph Pipeline.
Supports running individual stages, full end-to-end extraction, entity resolution, and data export.
"""

import asyncio
import argparse
import sys
import logging
from typing import List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Reconfigure stdout for UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.models.schemas import (
    StartupEntity,
    ProductEntity,
    ResearchPaperEntity,
    JobEntity,
    NewsEntity,
    EntityMappingLog,
)
from src.crawlers.bulk.papers_crawler import ResearchPapersCrawler
from src.crawlers.bulk.startups_crawler import StartupsCrawler
from src.crawlers.bulk.products_crawler import ProductsCrawler
from src.crawlers.freshness.news_crawler import NewsCrawler
from src.crawlers.freshness.jobs_crawler import JobsCrawler
from src.resolution.resolver import EntityResolver
from src.export.sheets_exporter import SheetsExporter
from src.config import config

console = Console(highlight=False)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


async def run_full_pipeline(target_count: int = 1000):
    console.print(Panel.fit(
        "[bold cyan]FrontierAtlas Global Intelligence Graph Pipeline[/bold cyan]\n"
        "[dim]Massive Bulk Ingestion | 24-Hour Freshness Signals | Entity Resolution | 6-Tab Export[/dim]",
        border_style="cyan"
    ))

    # Phase I: Massive Bulk Ingestion
    console.print("\n[bold yellow]=== PHASE I: MASSIVE BULK DATA ACQUISITION ===[/bold yellow]")
    papers_crawler = ResearchPapersCrawler()
    startups_crawler = StartupsCrawler()
    products_crawler = ProductsCrawler()

    with console.status("[bold green]Harvesting 1,000+ Research Papers (arXiv + OpenAlex + GitHub Stars)...[/bold green]"):
        papers: List[ResearchPaperEntity] = await papers_crawler.crawl(min_records=target_count)
    console.print(f"[bold green][+] Acquired {len(papers)} Research Papers with GitHub stars.[/bold green]")

    with console.status("[bold green]Harvesting 1,000+ Startups (HuggingFace + Venture Registries)...[/bold green]"):
        startups: List[StartupEntity] = await startups_crawler.crawl(min_records=target_count)
    console.print(f"[bold green][+] Acquired {len(startups)} Startups.[/bold green]")

    with console.status("[bold green]Harvesting 1,000+ Products & Tools (Spaces + Models + AI Catalog)...[/bold green]"):
        products: List[ProductEntity] = await products_crawler.crawl(min_records=target_count)
    console.print(f"[bold green][+] Acquired {len(products)} Products.[/bold green]")

    # Phase II: High-Fidelity 24-Hour Fresh Signal Ingestion
    console.print("\n[bold yellow]=== PHASE II: 24-HOUR FRESH SIGNAL INGESTION ===[/bold yellow]")
    news_crawler = NewsCrawler()
    jobs_crawler = JobsCrawler()

    with console.status("[bold green]Monitoring 5 AI News Feeds (< 24h Freshness & Full-Text)...[/bold green]"):
        news: List[NewsEntity] = await news_crawler.crawl()
    console.print(f"[bold green][+] Acquired {len(news)} 24-hour fresh News articles.[/bold green]")

    with console.status("[bold green]Monitoring 5 AI Job Boards (< 24h Freshness & Role Classification)...[/bold green]"):
        jobs: List[JobEntity] = await jobs_crawler.crawl()
    console.print(f"[bold green][+] Acquired {len(jobs)} 24-hour fresh Job postings.[/bold green]")

    # Phase IV: Deterministic Entity Resolution
    console.print("\n[bold yellow]=== PHASE IV: DETERMINISTIC ENTITY RESOLUTION ===[/bold yellow]")
    resolver = EntityResolver()
    mapping_logs: List[EntityMappingLog] = []

    with console.status("[bold green]Canonicalizing Startup & Product Entities and Building Audit Logs...[/bold green]"):
        # Resolve startups
        for s in startups:
            canon_name, log = resolver.resolve_startup(
                raw_name=s.content.entityName,
                source_url=s.source.url,
                website_url=s.content.data.website or "",
            )
            s.content.entityName = canon_name
            mapping_logs.append(log)

        # Resolve products
        for p in products:
            clean_prod, canon_startup, log = resolver.resolve_product(
                raw_product_name=p.content.productName,
                raw_startup_name=p.content.startupName,
                source_url=p.source.url,
            )
            p.content.productName = clean_prod
            p.content.startupName = canon_startup
            mapping_logs.append(log)

    console.print(f"[bold green][+] Generated {len(mapping_logs)} Entity Mapping Audit Logs.[/bold green]")

    # Close all client sessions cleanly
    await papers_crawler.client.close()
    await startups_crawler.client.close()
    await products_crawler.client.close()
    await news_crawler.client.close()
    await jobs_crawler.client.close()

    # Phase VI: 6-Tab Multi-Format Export
    console.print("\n[bold yellow]=== PHASE VI: 6-TAB EXPORT & GOOGLE SHEETS BUNDLE ===[/bold yellow]")
    exporter = SheetsExporter()
    with console.status("[bold green]Generating Stylized Excel (.xlsx), CSVs, and JSON Dumps...[/bold green]"):
        export_results = exporter.export_all(
            startups=startups,
            products=products,
            papers=papers,
            jobs=jobs,
            news=news,
            mapping_logs=mapping_logs,
        )

    # Summary Table
    table = Table(title="FrontierAtlas Ingestion Pipeline Summary", header_style="bold magenta")
    table.add_column("Tab Name / Entity", style="cyan")
    table.add_column("Count Extracted", justify="right", style="green")
    table.add_column("Validation Criteria", style="dim")

    table.add_row("Startups", f"{len(startups):,}", "Min. 1,000 unique records (YC & Registries)")
    table.add_row("Products", f"{len(products):,}", "Min. 1,000 unique records (Pricing Enums & Tags)")
    table.add_row("Research Papers", f"{len(papers):,}", "Min. 1,000 unique records (arXiv + GitHub Stars)")
    table.add_row("Jobs", f"{len(jobs):,}", "Strictly < 24-hr fresh (5 AI Job Boards)")
    table.add_row("News", f"{len(news):,}", "Strictly < 24-hr fresh full-text (5 News Sources)")
    table.add_row("Entity Mapping Log", f"{len(mapping_logs):,}", "Raw vs Canonical audit trail")

    console.print(table)
    console.print(f"\n[bold green][+] Workbook Generated:[/bold green] {export_results['excel']}")
    console.print(f"[bold green][+] CSV Directory:[/bold green] {export_results['csv_dir']}")
    console.print(f"[bold green][+] JSON Directory:[/bold green] {export_results['json_dir']}\n")


def main():
    parser = argparse.ArgumentParser(description="FrontierAtlas Intelligence Graph CLI")
    subparsers = parser.add_subparsers(dest="command", help="Pipeline subcommands")

    # run-all
    run_all_parser = subparsers.add_parser("run-all", help="Execute complete pipeline end-to-end")
    run_all_parser.add_argument("--target", type=int, default=1000, help="Target minimum records for Phase I")

    # papers
    papers_parser = subparsers.add_parser("papers", help="Harvest research papers with GitHub stars")
    papers_parser.add_argument("--limit", type=int, default=1000, help="Number of papers to harvest")

    # startups
    startups_parser = subparsers.add_parser("startups", help="Harvest startups from directories")
    startups_parser.add_argument("--limit", type=int, default=1000, help="Number of startups to harvest")

    # products
    products_parser = subparsers.add_parser("products", help="Harvest AI products and tools")
    products_parser.add_argument("--limit", type=int, default=1000, help="Number of products to harvest")

    # fresh
    subparsers.add_parser("fresh", help="Harvest 24-hour fresh news and job signals")

    # resolve
    subparsers.add_parser("resolve", help="Test entity resolution and canonicalization")

    # export
    subparsers.add_parser("export", help="Export existing or freshly crawled datasets")

    args = parser.parse_args()

    if args.command in (None, "run-all"):
        target = getattr(args, "target", 1000)
        asyncio.run(run_full_pipeline(target_count=target))
    elif args.command == "papers":
        crawler = ResearchPapersCrawler()
        papers = asyncio.run(crawler.crawl(min_records=args.limit))
        console.print(f"Harvested {len(papers)} research papers.")
    elif args.command == "startups":
        crawler = StartupsCrawler()
        startups = asyncio.run(crawler.crawl(min_records=args.limit))
        console.print(f"Harvested {len(startups)} startups.")
    elif args.command == "products":
        crawler = ProductsCrawler()
        products = asyncio.run(crawler.crawl(min_records=args.limit))
        console.print(f"Harvested {len(products)} products.")
    elif args.command == "fresh":
        news_crawler = NewsCrawler()
        jobs_crawler = JobsCrawler()
        news = asyncio.run(news_crawler.crawl())
        jobs = asyncio.run(jobs_crawler.crawl())
        console.print(f"Harvested {len(news)} fresh news and {len(jobs)} fresh jobs.")
    elif args.command == "resolve":
        resolver = EntityResolver()
        test_cases = [
            ("OpenAI, Inc.", "https://openai.com"),
            ("Open AI", "https://openai.com/about"),
            ("Anthropic PBC", "https://anthropic.com"),
            ("Mistral AI SAS", "https://mistral.ai"),
            ("Hugging Face, Inc.", "https://huggingface.co"),
            ("Scale AI Inc.", "https://scale.com"),
            ("Midjourney Inc", "https://midjourney.com"),
            ("ElevenLabs Inc.", "https://elevenlabs.io"),
        ]
        table = Table(title="Entity Resolution Test Bench", header_style="bold blue")
        table.add_column("Raw Name", style="cyan")
        table.add_column("Canonical Name", style="green")
        table.add_column("Method Used", style="magenta")
        table.add_column("Confidence", justify="right", style="yellow")

        for raw, url in test_cases:
            canon, log = resolver.resolve_startup(raw, source_url=url)
            table.add_row(log.raw_name, log.canonical_name, log.method_used, f"{log.confidence_score:.2f}")

        console.print(table)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
