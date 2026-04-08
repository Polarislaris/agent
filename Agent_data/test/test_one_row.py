"""
test_one_row.py — 最小化端到端测试
1. 从 SimplifyJobs GitHub README 解析第一条有效数据（不调用 AI，不访问招聘页）
2. 组装成 ScrapeDataResponse JSON 格式
3. POST 到 Java 后端 /api/interns/push-data
4. 再 GET /api/interns/db/status 验证数据已写入 Supabase

运行方式（在项目根目录下）：
    python Agent_data/test/test_one_row.py
"""

import hashlib
import re
import sys
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

# ─── 配置 ────────────────────────────────────────────────────────────────────
JAVA_BASE = "http://localhost:8080"
README_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/"
    "Summer2026-Internships/dev/README.md"
)
MAX_AGE_DAYS = 15


# ─── 工具函数 ─────────────────────────────────────────────────────────────────

def generate_id(title: str, company: str) -> str:
    raw = f"{title.strip().lower()}|{company.strip().lower()}"
    return hashlib.md5(raw.encode()).hexdigest()[:8]


def parse_age(age_str: str):
    age_str = age_str.strip().lower()
    m = re.match(r"^(\d+)\s*d$", age_str)
    if m:
        return int(m.group(1))
    m = re.match(r"^(\d+)\s*mo$", age_str)
    if m:
        return int(m.group(1)) * 30
    return None


def extract_apply_url(td_html: str) -> str:
    soup = BeautifulSoup(td_html, "html.parser")
    for a in soup.find_all("a", href=True):
        img = a.find("img")
        if img and img.get("alt") == "Apply":
            return a["href"]
    first_a = soup.find("a", href=True)
    return first_a["href"] if first_a else ""


def clean_company(raw: str) -> str:
    cleaned = re.sub(r"^[🔥🛂🇺🇸🎓\s]+", "", raw).strip()
    return cleaned.replace("↳", "").strip()


# ─── Step 1：从 README 解析第一条有效数据 ─────────────────────────────────────

def fetch_one_row():
    print("=== Step 1: 从 GitHub README 解析第一条有效数据 ===")
    print(f"  URL: {README_URL}")

    resp = requests.get(README_URL, timeout=30)
    resp.raise_for_status()
    print(f"  README 获取成功 ({len(resp.text):,} bytes)")

    today = datetime.now()
    last_company = ""

    table_pattern = re.compile(r"<table>.*?</table>", re.DOTALL)
    for table_html in table_pattern.findall(resp.text):
        soup = BeautifulSoup(table_html, "html.parser")
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 5:
                continue

            company_cell = cells[0].get_text(strip=True)
            title        = cells[1].get_text(strip=True)
            location     = cells[2].get_text(separator=", ", strip=True)
            apply_html   = str(cells[3])
            age_str      = cells[4].get_text(strip=True)

            # 跳过关闭的岗位
            if "🔒" in company_cell or "🔒" in title:
                continue

            age_days = parse_age(age_str)
            if age_days is None or age_days > MAX_AGE_DAYS:
                continue

            # 解析公司名
            clean_name = clean_company(company_cell)
            if not clean_name or company_cell.strip().startswith("↳"):
                clean_name = last_company
            else:
                last_company = clean_name

            title = re.sub(r"\s*🎓\s*$", "", title).strip()
            apply_link = extract_apply_url(apply_html)
            post_date  = (today - timedelta(days=age_days)).strftime("%Y-%m-%d")
            job_id     = generate_id(title, clean_name)

            row_data = {
                "job_id":    job_id,
                "company":   clean_name,
                "title":     title,
                "location":  location,
                "apply_url": apply_link,
                "post_date": post_date,
            }
            print(f"\n  ✅ 找到第一条有效数据:")
            for k, v in row_data.items():
                print(f"     {k:<12} = {v}")
            return row_data

    print("  ❌ 未找到任何有效数据！", file=sys.stderr)
    sys.exit(1)


# ─── Step 2：组装 JSON 并 POST 到 Java ────────────────────────────────────────

def push_to_java(row: dict):
    print("\n=== Step 2: 发送数据到 Java /api/interns/push-data ===")

    payload = {
        "jobs": [row],
        "job_documents": [
            {
                "job_id":       row["job_id"],
                "fetch_url":    row["apply_url"],
                "scrape_method": "test_one_row",
                "jd_raw_text":  f"[TEST] {row['company']} — {row['title']}"
            }
        ]
    }

    url = f"{JAVA_BASE}/api/interns/push-data"
    print(f"  POST {url}")
    print(f"  payload: jobs=[1条], job_documents=[1条]")

    resp = requests.post(url, json=payload, timeout=30)
    print(f"  HTTP {resp.status_code}")

    if resp.status_code != 200:
        print(f"  ❌ 接口返回错误: {resp.text}", file=sys.stderr)
        sys.exit(1)

    result = resp.json()
    print(f"  ✅ 接口响应: {result}")
    return result


# ─── Step 3：查询 DB 状态验证写入 ────────────────────────────────────────────

def verify_db(job_id: str):
    print("\n=== Step 3: 验证数据库写入 ===")

    # 查询总数状态
    status_url = f"{JAVA_BASE}/api/interns/db/status"
    resp = requests.get(status_url, timeout=10)
    status = resp.json()
    print(f"  DB 状态: jobs={status.get('jobs_count')}, "
          f"documents={status.get('documents_count')}")

    # 查询 Jobs 列表，检查 job_id 是否存在
    jobs_url = f"{JAVA_BASE}/api/interns/db/jobs"
    resp2 = requests.get(jobs_url, timeout=10)
    jobs = resp2.json()

    found = any(j.get("jobId") == job_id for j in jobs)
    if found:
        print(f"  ✅ job_id={job_id} 已在 Supabase Jobs 中找到！")
    else:
        print(f"  ⚠️  未找到 job_id={job_id}（可能已写入 job_documents 但 ON CONFLICT 跳过）")

    return found


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print(" 端到端最小测试: README → Python 解析 → Java → Supabase")
    print("=" * 60)

    # 1. 解析一行
    row = fetch_one_row()

    # 2. 写入数据库
    push_to_java(row)

    # 3. 验证
    verify_db(row["job_id"])

    print("\n" + "=" * 60)
    print(" 测试完成 ✅")
    print("=" * 60)
