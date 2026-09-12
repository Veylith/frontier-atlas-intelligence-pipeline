"""
PDF Generator script for FrontierAtlas Architecture Whitepaper.
Generates a 3-page technical design document using ReportLab.
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_PDF = BASE_DIR / "architecture.pdf"


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header
        self.drawString(54, 750, "FrontierAtlas Global Intelligence Graph — Technical Architecture & Scaling Strategy")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 744, 558, 744)

        # Footer
        self.line(54, 45, 558, 45)
        self.drawString(54, 32, "Confidential — GraphOne / FrontierAtlas Engineering")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_text)
        self.restoreState()


def build_pdf():
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=60,
        bottomMargin=55,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#475569"),
        spaceAfter=10,
    )

    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=10,
        spaceAfter=4,
    )

    h2_style = ParagraphStyle(
        "SectionH2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor("#2563EB"),
        spaceBefore=6,
        spaceAfter=3,
    )

    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#334155"),
        spaceAfter=5,
    )

    bullet_style = ParagraphStyle(
        "BulletCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#334155"),
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3,
    )

    callout_style = ParagraphStyle(
        "CalloutText",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#1E293B"),
    )

    story = []

    # ================= PAGE 1 =================
    story.append(Paragraph("FrontierAtlas Global Intelligence Graph Architecture", title_style))
    story.append(Paragraph("Autonomous Scalable Ingestion, Multi-Tier LLM Orchestration, & Deterministic Entity Resolution | 500k+ Scale Design", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2563EB"), spaceAfter=8))

    story.append(Paragraph("1. Executive Overview & System Topology", h1_style))
    story.append(Paragraph(
        "FrontierAtlas continuously ingests, structures, resolves, and enriches multi-dimensional signals across the AI venture ecosystem. "
        "The architecture reconciles the throughput of traditional web scrapers with the structured extraction power of LLMs, "
        "enforcing strict zero-hallucination policies, sub-24-hour freshness boundaries, and sub-millisecond graph queryability.",
        body_style
    ))

    # Architecture Topology Box
    topo_data = [
        [
            Paragraph("<b>Ingestion Sources:</b> arXiv, PapersWithCode, YC, Hugging Face, 5 AI News Feeds, 5 AI Job Boards, GitHub", callout_style),
            Paragraph("<b>Crawler Mesh:</b> Async aiohttp + Playwright Stealth + User-Agent Pool + Token Bucket Limiter", callout_style),
        ],
        [
            Paragraph("<b>Resilience Engine:</b> DOM Pruning (413 Immunity) + Gemini Flash / Groq Llama 3 / Heuristic Fallback", callout_style),
            Paragraph("<b>Resolution & Storage:</b> Deterministic Suffix Stripping + RapidFuzz + PostgreSQL / Neo4j / Qdrant", callout_style),
        ]
    ]
    t_topo = Table(topo_data, colWidths=[240, 260])
    t_topo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_topo)
    story.append(Spacer(1, 8))

    story.append(Paragraph("2. Scale Strategy: Harvesting 500,000+ Entities Autonomously", h1_style))
    story.append(Paragraph(
        "To scale to 500,000+ startups, products, research papers, and live market signals without human intervention, the system deploys a distributed orchestration mesh:",
        body_style
    ))

    story.append(Paragraph("• <b>Distributed URL Frontier & Workflows:</b> Orchestrated via <b>Temporal.io</b> and <b>Celery on Redis/RabbitMQ</b>. Implements partitioned URL priority queues with per-domain rate limiting, ensuring polite concurrent crawling without triggering IP bans.", bullet_style))
    story.append(Paragraph("• <b>Autoscaling Worker Fleet:</b> Kubernetes Event-driven Autoscaling (KEDA) dynamically scales crawler worker pods from 5 to 150 instances based on queue depth and endpoint responsiveness.", bullet_style))
    story.append(Paragraph("• <b>High-Throughput Research Harvesting:</b> Bulk OAI-PMH harvest protocol for arXiv combined with PapersWithCode open metadata dumps to process hundreds of thousands of papers into partitioned S3 Parquet datasets in minutes.", bullet_style))
    story.append(Paragraph("• <b>Dynamic GitHub Metrics Tracking:</b> Pooled authenticated GitHub GraphQL workers with unauthenticated HTML regex scrapers resolve live stargazers, forks, and commit velocities across 100k+ repositories with continuous caching.", bullet_style))

    story.append(PageBreak())

    # ================= PAGE 2 =================
    story.append(Paragraph("3. Resilient LLM Orchestration: Managing 413s & 429s", h1_style))
    story.append(Paragraph(
        "LLM pipelines in production frequently fail due to payload size overflows (HTTP 413) and aggressive rate limits (HTTP 429). FrontierAtlas guarantees zero-downtime execution via a multi-tier defense:",
        body_style
    ))

    story.append(Paragraph("A. 413 Payload Too Large Elimination (Semantic Chunking & DOM Pruning)", h2_style))
    story.append(Paragraph("• <b>AST / DOM Tree Pruning:</b> Strips non-semantic elements (&lt;script&gt;, &lt;style&gt;, &lt;svg&gt;, &lt;iframe&gt;, base64 images, navbars, footers).", bullet_style))
    story.append(Paragraph("• <b>Semantic Density Condenser:</b> Translates cleaned DOM structures into dense markdown representations preserving headings, tables, and JSON-LD schema.", bullet_style))
    story.append(Paragraph("• <b>Sliding Window with Overlap:</b> Enforces a strict 3,500-token chunk window with 250-token overlap, ensuring payloads never breach provider context limits.", bullet_style))

    story.append(Paragraph("B. 429 Rate Limit Mitigation & Multi-Tier Fallback Chain", h2_style))
    story.append(Paragraph("• <b>Token Bucket Rate Limiting:</b> In-memory and Redis token buckets enforce client-side RPM and TPM ceilings per API provider.", bullet_style))
    story.append(Paragraph("• <b>Full Jitter Exponential Backoff:</b> <i>Delay = uniform(0.1, min(Cap, Base × 2^attempt))</i>. Eliminates thundering-herd retry storms across workers while parsing explicit Retry-After headers.", bullet_style))
    story.append(Paragraph("• <b>Multi-Tier Circuit Breaker Chain:</b>", bullet_style))
    story.append(Paragraph("   - <i>Tier 1 (Primary):</i> Gemini 1.5 / 2.0 Flash (Fast JSON mode, high context, cost-efficient).", bullet_style))
    story.append(Paragraph("   - <i>Tier 2 (Failover):</i> Groq Llama 3.3 70B / 8B (Sub-second low-latency inference).", bullet_style))
    story.append(Paragraph("   - <i>Tier 3 (Local Fail-Safe):</i> Deterministic Rule-Based Heuristics (Guarantees 100% uptime during global API outages).", bullet_style))

    story.append(Spacer(1, 6))
    story.append(Paragraph("4. Freshness Tracking: 24-Hour Guarantee & Zero-Duplicate Crawling", h1_style))
    story.append(Paragraph(
        "Extreme freshness is enforced across 5 AI news feeds and 5 AI job boards to guarantee market intelligence reflects events in the preceding 24-hour window:",
        body_style
    ))

    story.append(Paragraph("• <b>Distributed Bloom Filter Deduplication:</b> Redis Scalable Bloom Filters store SHA-256 signatures of (entity_id + source_url) with &lt; 0.001% false positive rate.", bullet_style))
    story.append(Paragraph("• <b>Content Hash Deltas:</b> Computes cryptographic hashes of article bodies to detect content alterations and avoid redundant processing.", bullet_style))
    story.append(Paragraph("• <b>HTTP Conditional Requests:</b> Automates ETag and If-Modified-Since headers to bypass un-updated sites via HTTP 304 Not Modified.", bullet_style))
    story.append(Paragraph("• <b>Precision Date Normalization:</b> Custom parsing pipeline resolving ISO-8601, RFC-2822, UNIX epoch, JSON-LD microdata, and relative human timestamps ('2 hours ago', 'yesterday') with strict 24.0-hour boundary enforcement.", bullet_style))

    story.append(PageBreak())

    # ================= PAGE 3 =================
    story.append(Paragraph("5. Deterministic Entity Resolution Engine", h1_style))
    story.append(Paragraph(
        "Normalizes noisy, heterogeneous entity representations (e.g. 'OpenAI, Inc.', 'Open AI', 'openai.com') into canonical nodes in the Intelligence Graph:",
        body_style
    ))

    story.append(Paragraph("• <b>Rule-Based Normalizer:</b> Strips legal suffixes (Inc, LLC, Ltd, Corp, PBC, GmbH, SAS, Pte Ltd, Labs, Technologies) and extraneous punctuation.", bullet_style))
    story.append(Paragraph("• <b>Domain & Hostname Matching:</b> Maps root domain URLs to canonical startup organizations with 0.95+ confidence.", bullet_style))
    story.append(Paragraph("• <b>Hybrid Fuzzy Matching:</b> RapidFuzz composite scoring combining Token Sort Ratio and Jaro-Winkler similarity against a 50+ entity seed database (Threshold >= 0.85).", bullet_style))
    story.append(Paragraph("• <b>Immutable Audit Trail:</b> Generates Entity Mapping Logs recording raw_name, canonical_name, confidence_score, method_used, and source_url.", bullet_style))

    story.append(Paragraph("6. Anti-Bot Navigation & Stealth Strategy", h1_style))
    story.append(Paragraph(
        "Bypasses Cloudflare Turnstile, Datadome, and Akamai on high-value intelligence sources via layered evasion techniques:",
        body_style
    ))
    story.append(Paragraph("• <b>Browser Fingerprint Realism:</b> Rotates realistic User-Agents matching Client Hints (sec-ch-ua, sec-ch-ua-platform, Sec-Fetch-*).", bullet_style))
    story.append(Paragraph("• <b>Playwright Async Stealth:</b> Evasions patching navigator.webdriver, WebGL parameters, canvas noise, and human-like bezier mouse paths for JavaScript SPAs.", bullet_style))
    story.append(Paragraph("• <b>Residential Proxy Mesh:</b> Domain-pinned sticky IP rotation through residential backbones.", bullet_style))

    story.append(Paragraph("7. Polyglot Storage Architecture & Deliverables Summary", h1_style))

    storage_table_data = [
        [Paragraph("<b>Storage Layer</b>", callout_style), Paragraph("<b>Technology</b>", callout_style), Paragraph("<b>Role & Justification</b>", callout_style)],
        [Paragraph("Relational / Events", body_style), Paragraph("PostgreSQL + TimescaleDB", body_style), Paragraph("Canonical entity metadata, time-series star metrics, ACID logs", body_style)],
        [Paragraph("Knowledge Graph", body_style), Paragraph("Neo4j / Memgraph", body_style), Paragraph("Multi-dimensional graph edges (Startup -> Product -> Paper -> Repo)", body_style)],
        [Paragraph("Vector Store", body_style), Paragraph("Qdrant / pgvector", body_style), Paragraph("Dense semantic embeddings for hybrid search & discovery", body_style)],
        [Paragraph("Data Lakehouse", body_style), Paragraph("Parquet on S3 / Iceberg", body_style), Paragraph("Petabyte-scale historical analytics and cold snapshot archive", body_style)],
    ]
    t_storage = Table(storage_table_data, colWidths=[100, 130, 270])
    t_storage.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_storage)
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>Trial Deliverables Summary:</b>", h2_style))
    story.append(Paragraph("✔ <b>6 Output Tabs:</b> Startups (1,000+), Products (1,000+), Research Papers (1,000+ with GitHub stars), Jobs (24h fresh), News (24h fresh full-text), Entity Mapping Log.", body_style))
    story.append(Paragraph("✔ <b>Engineering Codebase:</b> Complete async pipeline CLI, unit test suite, and automated Google Sheets / Excel / JSON export engines.", body_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated architecture whitepaper at: {OUTPUT_PDF}")


if __name__ == "__main__":
    build_pdf()
