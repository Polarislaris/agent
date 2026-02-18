"""
Pydantic models — matches Java InternPost / CompanyInfo
"""
from typing import List
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
        "populate_by_name": True,       # allow using field names (e.g. applyLink) when creating instances
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
