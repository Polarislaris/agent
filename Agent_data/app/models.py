"""
Pydantic models — matches Java InternPost / CompanyInfo + DB-oriented models
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CompanyInfo(BaseModel):
    size: str = Field(..., examples=["50–200 employees"])
    founded: str = Field(..., examples=["2021"])
    business: str = Field(..., examples=["Mobility & transportation platform"])


class InternPost(BaseModel):
    id: str
    title: str
    company: str
    base: str                         # location
    date: str                         # date YYYY-MM-DD
    description: str
    requirements: List[str]
    applyLink: str = Field(..., alias="applyLink")
    companyInfo: CompanyInfo = Field(..., alias="companyInfo")
    fitScore: str = Field(..., alias="fitScore")
    difficulty: str = Field(..., alias="difficulty")
    avgSalary: str = Field(..., alias="avgSalary")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "id": "1",
                "title": "Full-Stack Intern",
                "company": "Dryft",
                "base": "San Francisco, CA",
                "date": "2026-02-16",
                "description": "Join the engineering team...",
                "requirements": ["React", "Node.js", "SQL"],
                "applyLink": "https://example.com/apply",
                "companyInfo": {
                    "size": "50–200 employees",
                    "founded": "2021",
                    "business": "Mobility & transportation platform"
                },
                "fitScore": "★★★★☆  Strong match",
                "difficulty": "Medium",
                "avgSalary": "$45–55/hr"
            }
        }
    }


# ─── DB-oriented models for scrape-data endpoint ────────────────────────────

class JobRow(BaseModel):
    """Matches Supabase 'Jobs' table schema"""
    job_id: str
    company: str
    title: str
    location: str
    apply_url: str
    post_date: str  # YYYY-MM-DD


class JobDocumentRow(BaseModel):
    """Matches Supabase 'job_documents' table schema"""
    job_id: str
    fetch_url: str = ""
    scrape_method: str = ""
    jd_raw_text: str = ""


class ScrapeDataResponse(BaseModel):
    """Response for /api/v1/scrape-data endpoint"""
    jobs: List[JobRow]
    job_documents: List[JobDocumentRow]


# ─── Cleaning API models for Java -> Python -> Java flow ───────────────────

class JobDocumentCleanInput(BaseModel):
    job_id: str
    jd_raw_text: str = ""


class JobDocumentCleanRequest(BaseModel):
    documents: List[JobDocumentCleanInput]
    min_length: int = 50


class JobDocumentCleanResult(BaseModel):
    job_id: str
    jd_clean_text: str = ""
    jd_clean_hash: str = ""
    delete_row: bool = False
    cleaned_length: int = 0


class JobDocumentCleanResponse(BaseModel):
    results: List[JobDocumentCleanResult]
    total: int
    keep_count: int
    delete_count: int
