"""
Configuration module for FrontierAtlas Pipeline.
Handles directory paths, API credentials, timeouts, retry configurations, and crawler settings.
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field

# Base Directory Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs"

DATA_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)


class PipelineConfig(BaseModel):
    # Concurrency & Network
    max_concurrent_requests: int = Field(default=25, description="Max concurrent async requests")
    request_timeout_seconds: int = Field(default=20, description="HTTP request timeout in seconds")
    max_retries: int = Field(default=3, description="Max retry attempts per request")
    backoff_factor: float = Field(default=1.5, description="Base exponential backoff factor")
    
    # Target Ingestion Volumes (Phase I)
    target_startups: int = Field(default=1000, description="Target minimum startups")
    target_products: int = Field(default=1000, description="Target minimum products")
    target_papers: int = Field(default=1000, description="Target minimum research papers")
    
    # Freshness Threshold (Phase II)
    freshness_window_hours: int = Field(default=24, description="Freshness threshold in hours")
    
    # LLM API Keys (Supports environment variables with graceful fallback)
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    groq_api_key: str = Field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    deepseek_api_key: str = Field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    github_token: str = Field(default_factory=lambda: os.getenv("GITHUB_TOKEN", ""))
    
    # Export Filepaths
    export_excel_path: Path = DATA_DIR / "FrontierAtlas_Intelligence_Graph.xlsx"
    export_json_dir: Path = DATA_DIR / "json"
    export_csv_dir: Path = DATA_DIR / "csv"


config = PipelineConfig()
config.export_json_dir.mkdir(parents=True, exist_ok=True)
config.export_csv_dir.mkdir(parents=True, exist_ok=True)
