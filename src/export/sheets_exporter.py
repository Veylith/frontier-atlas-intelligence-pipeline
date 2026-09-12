"""
Multi-Tab Exporter for Google Sheets, Excel (.xlsx), CSV, and JSON.
Generates all 6 required tabs matching the exact specified schema structures:
1. Startups (Min. 1,000 rows)
2. Products (Min. 1,000 rows)
3. Research Papers (Min. 1,000 rows with GitHub stars)
4. Jobs (24-hr fresh)
5. News (24-hr fresh full-text)
6. Entity Mapping Log (Audit trail)
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Union
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from src.models.schemas import (
    StartupEntity,
    ProductEntity,
    ResearchPaperEntity,
    JobEntity,
    NewsEntity,
    EntityMappingLog,
)
from src.config import config

logger = logging.getLogger("SheetsExporter")


class SheetsExporter:
    def __init__(
        self,
        output_excel_path: Path = config.export_excel_path,
        csv_dir: Path = config.export_csv_dir,
        json_dir: Path = config.export_json_dir,
    ):
        self.excel_path = output_excel_path
        self.csv_dir = csv_dir
        self.json_dir = json_dir
        self.csv_dir.mkdir(parents=True, exist_ok=True)
        self.json_dir.mkdir(parents=True, exist_ok=True)

    def _format_startups_df(self, startups: List[StartupEntity]) -> pd.DataFrame:
        rows = []
        for s in startups:
            rows.append({
                "schemaVersion": s.schemaVersion,
                "recordType": s.recordType,
                "source.name": s.source.name,
                "source.url": s.source.url,
                "content.entityName": s.content.entityName,
                "content.data.employeeCount": s.content.data.employeeCount if s.content.data.employeeCount is not None else "",
                "content.data.description": s.content.data.description or "",
                "content.data.website": s.content.data.website or "",
                "content.data.foundedYear": s.content.data.foundedYear or "",
                "content.data.categories": ", ".join(s.content.data.categories) if s.content.data.categories else "",
                "content.data.headquarters": s.content.data.headquarters or "",
                "collectedAt": s.collectedAt,
            })
        return pd.DataFrame(rows)

    def _format_products_df(self, products: List[ProductEntity]) -> pd.DataFrame:
        rows = []
        for p in products:
            rows.append({
                "schemaVersion": p.schemaVersion,
                "recordType": p.recordType,
                "source.name": p.source.name,
                "source.url": p.source.url,
                "content.productName": p.content.productName,
                "content.startupName": p.content.startupName,
                "content.pricingModel": p.content.pricingModel.value if hasattr(p.content.pricingModel, "value") else str(p.content.pricingModel),
                "content.description": p.content.description or "",
                "content.category": p.content.category or "",
                "content.website_url": p.content.website_url or "",
                "collectedAt": p.collectedAt,
            })
        return pd.DataFrame(rows)

    def _format_papers_df(self, papers: List[ResearchPaperEntity]) -> pd.DataFrame:
        rows = []
        for p in papers:
            rows.append({
                "schemaVersion": p.schemaVersion,
                "recordType": p.recordType,
                "content.title": p.content.title,
                "content.authors": ", ".join(p.content.authors) if p.content.authors else "",
                "content.paper_url": p.content.paper_url,
                "content.github_url": p.content.github_url or "",
                "content.github_stars": p.content.github_stars,
                "content.published_date": p.content.published_date,
                "content.primary_category": p.content.primary_category or "cs.AI",
                "collectedAt": p.collectedAt,
            })
        return pd.DataFrame(rows)

    def _format_jobs_df(self, jobs: List[JobEntity]) -> pd.DataFrame:
        rows = []
        for j in jobs:
            rows.append({
                "schemaVersion": j.schemaVersion,
                "recordType": j.recordType,
                "content.company": j.content.company,
                "content.title": j.content.title,
                "content.date": j.content.date,
                "content.is_remote": j.content.is_remote,
                "content.role_family": j.content.role_family,
                "content.source_url": j.content.source_url,
                "content.location": j.content.location or "",
                "content.description_snippet": j.content.description_snippet or "",
                "collectedAt": j.collectedAt,
            })
        return pd.DataFrame(rows)

    def _format_news_df(self, news: List[NewsEntity]) -> pd.DataFrame:
        rows = []
        for n in news:
            rows.append({
                "schemaVersion": n.schemaVersion,
                "recordType": n.recordType,
                "content.title": n.content.title,
                "content.summary": n.content.summary,
                "content.full_text": n.content.full_text,
                "content.source_name": n.content.source_name,
                "content.source_url": n.content.source_url,
                "content.published_date": n.content.published_date,
                "content.tags": ", ".join(n.content.tags) if n.content.tags else "",
                "collectedAt": n.collectedAt,
            })
        return pd.DataFrame(rows)

    def _format_mapping_log_df(self, logs: List[EntityMappingLog]) -> pd.DataFrame:
        rows = []
        for l in logs:
            rows.append({
                "raw_name": l.raw_name,
                "canonical_name": l.canonical_name,
                "entity_type": l.entity_type,
                "confidence_score": l.confidence_score,
                "method_used": l.method_used,
                "matched_alias": l.matched_alias or "",
                "source_url": l.source_url,
                "timestamp": l.timestamp,
            })
        return pd.DataFrame(rows)

    def export_all(
        self,
        startups: List[StartupEntity],
        products: List[ProductEntity],
        papers: List[ResearchPaperEntity],
        jobs: List[JobEntity],
        news: List[NewsEntity],
        mapping_logs: List[EntityMappingLog],
    ) -> Dict[str, Path]:
        """
        Exports all 6 datasets to:
        1. CSV files for individual tabs
        2. Multi-tab stylized Excel file (.xlsx) ready for Google Sheets upload
        3. Canonical JSON dumps
        """
        logger.info("Exporting all datasets to CSV, Excel, and JSON...")

        df_startups = self._format_startups_df(startups)
        df_products = self._format_products_df(products)
        df_papers = self._format_papers_df(papers)
        df_jobs = self._format_jobs_df(jobs)
        df_news = self._format_news_df(news)
        df_mapping = self._format_mapping_log_df(mapping_logs)

        # 1. Export CSVs
        csv_files = {
            "Startups": self.csv_dir / "Startups.csv",
            "Products": self.csv_dir / "Products.csv",
            "Research Papers": self.csv_dir / "ResearchPapers.csv",
            "Jobs": self.csv_dir / "Jobs.csv",
            "News": self.csv_dir / "News.csv",
            "Entity Mapping Log": self.csv_dir / "EntityMappingLog.csv",
        }

        df_startups.to_csv(csv_files["Startups"], index=False, encoding="utf-8-sig")
        df_products.to_csv(csv_files["Products"], index=False, encoding="utf-8-sig")
        df_papers.to_csv(csv_files["Research Papers"], index=False, encoding="utf-8-sig")
        df_jobs.to_csv(csv_files["Jobs"], index=False, encoding="utf-8-sig")
        df_news.to_csv(csv_files["News"], index=False, encoding="utf-8-sig")
        df_mapping.to_csv(csv_files["Entity Mapping Log"], index=False, encoding="utf-8-sig")

        # 2. Export JSON files
        json_dumps = {
            "startups.json": [s.model_dump() for s in startups],
            "products.json": [p.model_dump() for p in products],
            "research_papers.json": [p.model_dump() for p in papers],
            "jobs.json": [j.model_dump() for j in jobs],
            "news.json": [n.model_dump() for n in news],
            "entity_mapping_log.json": [m.model_dump() for m in mapping_logs],
        }
        for name, data in json_dumps.items():
            with open(self.json_dir / name, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        # 3. Export Multi-Tab Styled Excel Workbook
        with pd.ExcelWriter(self.excel_path, engine="openpyxl") as writer:
            df_startups.to_excel(writer, sheet_name="Startups", index=False)
            df_products.to_excel(writer, sheet_name="Products", index=False)
            df_papers.to_excel(writer, sheet_name="Research Papers", index=False)
            df_jobs.to_excel(writer, sheet_name="Jobs", index=False)
            df_news.to_excel(writer, sheet_name="News", index=False)
            df_mapping.to_excel(writer, sheet_name="Entity Mapping Log", index=False)

        # Apply rich styling to the Excel workbook
        self._style_excel_workbook(self.excel_path)

        logger.info(f"Export completed! Generated workbook at: {self.excel_path}")
        return {
            "excel": self.excel_path,
            "csv_dir": self.csv_dir,
            "json_dir": self.json_dir,
        }

    def _style_excel_workbook(self, filepath: Path):
        """Applies professional typography, header colors, borders, and column autosizing."""
        wb = openpyxl.load_workbook(filepath)
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        regular_font = Font(name="Segoe UI", size=10)
        thin_border = Border(
            left=Side(style="thin", color="E2E8F0"),
            right=Side(style="thin", color="E2E8F0"),
            top=Side(style="thin", color="E2E8F0"),
            bottom=Side(style="thin", color="E2E8F0"),
        )

        for sheet in wb.sheetnames:
            ws = wb[sheet]
            ws.views.sheetView[0].showGridLines = True

            # Style header row
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

            # Style data cells and adjust column width
            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    cell.border = thin_border
                    if cell.row > 1:
                        cell.font = regular_font
                        cell.alignment = Alignment(vertical="center")
                    val_str = str(cell.value or "")
                    if len(val_str) > max_len:
                        max_len = len(val_str)

                ws.column_dimensions[col_letter].width = min(max(max_len + 3, 14), 60)

        wb.save(filepath)
