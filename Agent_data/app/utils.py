"""
Data cleaning / utility functions
"""
import re
import hashlib
from typing import List


def generate_id(title: str, company: str, location: str = "") -> str:
    """Generate short hash id from title + company + location"""
    raw = f"{title.strip().lower()}|{company.strip().lower()}|{location.strip().lower()}"
    return hashlib.md5(raw.encode()).hexdigest()[:8]


def extract_skills(description: str) -> List[str]:
    """
    Extract tech keywords from job description
    TODO: Replace with NLP/LLM extraction
    """
    known = [
        "React", "Node.js", "TypeScript", "JavaScript", "Python", "Java",
        "Spring Boot", "SQL", "PostgreSQL", "MongoDB", "Docker", "Kubernetes",
        "AWS", "GCP", "Azure", "C++", "C/C++", "CUDA", "Swift", "SwiftUI",
        "Xcode", "Terraform", "CI/CD", "REST APIs", "GraphQL", "PyTorch",
        "TensorFlow", "Spark", "Kafka", "Go", "Rust", "Flutter",
    ]
    found: List[str] = []
    desc_lower = description.lower()
    for skill in known:
        if skill.lower() in desc_lower and skill not in found:
            found.append(skill)
    return found


def clean_html(text: str) -> str:
    """Remove HTML tags, keep plain text"""
    return re.sub(r"<[^>]+>", "", text).strip()


def truncate(text: str, max_len: int = 800) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "…"
