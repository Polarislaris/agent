#!/usr/bin/env python3
"""
Clean job_documents.jd_raw_text and write to jd_clean_text.

Rules implemented:
1) Remove HTML tags
2) Remove extra blank lines
3) Remove duplicated spaces
4) Normalize bullet symbols
5) Normalize full-width/half-width and special characters
6) Keep line breaks
7) Delete row if cleaned text length < min_length (default: 50)

Run examples:
  python clean_job_documents.py
  python clean_job_documents.py --dry-run
  python clean_job_documents.py --min-length 50 --limit 200

Environment overrides (optional):
  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
  APP_PROPERTIES_PATH
"""

from __future__ import annotations

import argparse
import hashlib
import html
import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import parse_qs, urlparse

import psycopg2
from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APP_PROPERTIES = PROJECT_ROOT / "backend/agent/src/main/resources/application.properties"


@dataclass
class DbConfig:
    host: str
    port: int
    dbname: str
    user: str
    password: str
    sslmode: Optional[str] = None
    connect_timeout: Optional[int] = None


def _load_properties(path: Path) -> Dict[str, str]:
    props: Dict[str, str] = {}
    if not path.exists():
        raise FileNotFoundError(f"application.properties not found: {path}")

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        props[key.strip()] = value.strip()
    return props


def _jdbc_to_db_config(jdbc_url: str, username: str, password: str) -> DbConfig:
    if not jdbc_url.startswith("jdbc:"):
        raise ValueError(f"unsupported jdbc url: {jdbc_url}")

    parsed = urlparse(jdbc_url[len("jdbc:") :])
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    dbname = (parsed.path or "/postgres").lstrip("/")

    qs = parse_qs(parsed.query)
    sslmode = qs.get("sslmode", [None])[0]

    connect_timeout = None
    raw_timeout = qs.get("connectTimeout", [None])[0]
    if raw_timeout and raw_timeout.isdigit():
        connect_timeout = int(raw_timeout)

    return DbConfig(
        host=host,
        port=port,
        dbname=dbname,
        user=username,
        password=password,
        sslmode=sslmode,
        connect_timeout=connect_timeout,
    )


def load_db_config() -> DbConfig:
    env_host = os.getenv("DB_HOST")
    env_port = os.getenv("DB_PORT")
    env_name = os.getenv("DB_NAME")
    env_user = os.getenv("DB_USER")
    env_password = os.getenv("DB_PASSWORD")

    if env_host and env_name and env_user and env_password:
        return DbConfig(
            host=env_host,
            port=int(env_port or "5432"),
            dbname=env_name,
            user=env_user,
            password=env_password,
            sslmode=os.getenv("DB_SSLMODE"),
            connect_timeout=int(os.getenv("DB_CONNECT_TIMEOUT", "0") or 0) or None,
        )

    properties_path = Path(os.getenv("APP_PROPERTIES_PATH", str(DEFAULT_APP_PROPERTIES)))
    props = _load_properties(properties_path)

    jdbc_url = props.get("spring.datasource.url")
    username = props.get("spring.datasource.username")
    password = props.get("spring.datasource.password")

    if not jdbc_url or not username or not password:
        raise ValueError(
            "database config is incomplete; set env vars or provide spring.datasource.* in application.properties"
        )

    return _jdbc_to_db_config(jdbc_url, username, password)


TRANSLATION_TABLE = str.maketrans(
    {
        "\u00A0": " ",
        "\u200B": "",
        "\u200C": "",
        "\u200D": "",
        "\uFEFF": "",
        "\u2018": "'",
        "\u2019": "'",
        "\u201C": '"',
        "\u201D": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\t": " ",
    }
)

_BULLET_PATTERN = re.compile(r"^\s*[•●◦▪▫■□◆◇▶▷►▸▹‣∙·・‧◉○*]\s*")
_DASH_BULLET_PATTERN = re.compile(r"^\s*[-–—]\s+")
_MULTI_SPACES = re.compile(r"[ \u00A0]{2,}")


def clean_jd_text(raw_text: str) -> str:
    text = raw_text or ""
    text = html.unescape(text)
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(TRANSLATION_TABLE)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove HTML tags while preserving logical line breaks.
    text = BeautifulSoup(text, "html.parser").get_text(separator="\n")

    cleaned_lines = []
    for line in text.split("\n"):
        line = line.strip()
        line = _BULLET_PATTERN.sub("- ", line)
        line = _DASH_BULLET_PATTERN.sub("- ", line)
        line = _MULTI_SPACES.sub(" ", line)
        cleaned_lines.append(line)

    # Collapse consecutive blank lines but keep paragraph structure.
    compact_lines = []
    previous_blank = False
    for line in cleaned_lines:
        if line == "":
            if not previous_blank:
                compact_lines.append("")
            previous_blank = True
        else:
            compact_lines.append(line)
            previous_blank = False

    return "\n".join(compact_lines).strip()


def process_job_documents(min_length: int, limit: Optional[int], dry_run: bool) -> None:
    cfg = load_db_config()

    conn_kwargs = {
        "host": cfg.host,
        "port": cfg.port,
        "dbname": cfg.dbname,
        "user": cfg.user,
        "password": cfg.password,
    }
    if cfg.sslmode:
        conn_kwargs["sslmode"] = cfg.sslmode
    if cfg.connect_timeout:
        conn_kwargs["connect_timeout"] = cfg.connect_timeout

    select_sql = (
        "SELECT job_id, jd_raw_text FROM job_documents "
        "WHERE jd_raw_text IS NOT NULL AND btrim(jd_raw_text) <> '' "
        "ORDER BY job_id"
    )
    if limit and limit > 0:
        select_sql += " LIMIT %s"

    updated = 0
    deleted = 0
    unchanged = 0
    scanned = 0

    with psycopg2.connect(**conn_kwargs) as conn:
        with conn.cursor() as cur:
            if limit and limit > 0:
                cur.execute(select_sql, (limit,))
            else:
                cur.execute(select_sql)
            rows = cur.fetchall()

            for job_id, raw_text in rows:
                scanned += 1
                cleaned = clean_jd_text(raw_text or "")

                if len(cleaned) < min_length:
                    deleted += 1
                    if not dry_run:
                        cur.execute("DELETE FROM job_documents WHERE job_id = %s", (job_id,))
                    continue

                clean_hash = hashlib.md5(cleaned.encode("utf-8")).hexdigest()

                if raw_text == cleaned:
                    unchanged += 1

                updated += 1
                if not dry_run:
                    cur.execute(
                        "UPDATE job_documents "
                        "SET jd_clean_text = %s, jd_clean_hash = %s "
                        "WHERE job_id = %s",
                        (cleaned, clean_hash, job_id),
                    )

        if dry_run:
            conn.rollback()
        else:
            conn.commit()

    mode = "DRY-RUN" if dry_run else "COMMIT"
    print(f"[{mode}] scanned={scanned}, updated={updated}, deleted={deleted}, unchanged={unchanged}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean job_documents.jd_raw_text into jd_clean_text")
    parser.add_argument("--min-length", type=int, default=50, help="delete row when cleaned text length is below this value")
    parser.add_argument("--limit", type=int, default=0, help="only process first N rows (0 means all)")
    parser.add_argument("--dry-run", action="store_true", help="show effect without committing changes")
    args = parser.parse_args()

    process_job_documents(
        min_length=args.min_length,
        limit=(args.limit if args.limit > 0 else None),
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
