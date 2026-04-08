#!/usr/bin/env python3
"""
调试脚本：只运行 Python 爬取，在控制台输出要发给 Java 的 Jobs + job_documents 数据。
用法: cd Agent_data && python test_scrape_output.py
"""
import sys
import os
import json
import logging

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(__file__))

# 加载 .env
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s — %(message)s",
)
logger = logging.getLogger("test_scrape")

from app.scraper import scrape_for_db_sync


def main():
    logger.info("=" * 60)
    logger.info("开始爬取（scrape_for_db_sync）...")
    logger.info("=" * 60)

    result = scrape_for_db_sync(limit=200)

    jobs = result.get("jobs", [])
    docs = result.get("job_documents", [])

    # ── 输出 Jobs 表数据 ─────────────────────────────────────────
    print("\n" + "=" * 80)
    print(f"  Jobs 表数据（共 {len(jobs)} 条）")
    print("=" * 80)

    for i, job in enumerate(jobs, 1):
        company = job.get("company", "")
        title = job.get("title", "")
        location = job.get("location", "")
        apply_url = job.get("apply_url", "")
        post_date = job.get("post_date", "")
        job_id = job.get("job_id", "")

        # 标记可能有问题的字段
        flags = []
        if not company: flags.append("❌company空")
        if not title: flags.append("❌title空")
        if not apply_url: flags.append("❌apply_url空")
        if not post_date: flags.append("❌post_date空")
        if not location: flags.append("⚠️location空")

        flag_str = f"  {'  '.join(flags)}" if flags else ""

        print(f"\n  [{i:3d}] job_id={job_id}")
        print(f"        company  : {company}")
        print(f"        title    : {title}")
        print(f"        location : {location or '(空)'}")
        print(f"        apply_url: {apply_url[:80]}{'...' if len(apply_url) > 80 else ''}")
        print(f"        post_date: {post_date}")
        if flag_str:
            print(f"        {flag_str}")

    # ── 输出 job_documents 表数据摘要 ────────────────────────────
    print("\n" + "=" * 80)
    print(f"  job_documents 表数据（共 {len(docs)} 条）")
    print("=" * 80)

    jd_lengths = []
    for i, doc in enumerate(docs, 1):
        job_id = doc.get("job_id", "")
        fetch_url = doc.get("fetch_url", "")
        method = doc.get("scrape_method", "")
        jd_text = doc.get("jd_raw_text", "")
        jd_len = len(jd_text)
        jd_lengths.append(jd_len)

        # 标记问题字段
        flags = []
        if not fetch_url: flags.append("❌fetch_url空")
        if not method: flags.append("❌method空")
        if not jd_text: flags.append("❌jd_raw_text空")
        elif jd_len < 100: flags.append(f"⚠️JD太短({jd_len}字)")

        flag_str = f"  {'  '.join(flags)}" if flags else ""

        print(f"\n  [{i:3d}] job_id={job_id}")
        print(f"        method   : {method}")
        print(f"        fetch_url: {fetch_url[:80]}{'...' if len(fetch_url) > 80 else ''}")
        print(f"        jd_length: {jd_len} 字符")
        print(f"        jd_preview: {jd_text[:120]}{'...' if jd_len > 120 else ''}")
        if flag_str:
            print(f"        {flag_str}")

    # ── 统计摘要 ─────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("  统计摘要")
    print("=" * 80)
    print(f"  Jobs 总数      : {len(jobs)}")
    print(f"  Documents 总数 : {len(docs)}")

    if jd_lengths:
        print(f"  JD 最短       : {min(jd_lengths)} 字符")
        print(f"  JD 最长       : {max(jd_lengths)} 字符")
        print(f"  JD 平均       : {sum(jd_lengths) // len(jd_lengths)} 字符")
        short_count = sum(1 for l in jd_lengths if l < 100)
        print(f"  JD < 100字    : {short_count} 条")

    # 检查 scrape_method 分布
    methods = {}
    for doc in docs:
        m = doc.get("scrape_method", "unknown")
        methods[m] = methods.get(m, 0) + 1
    print(f"\n  JD 爬取方法分布:")
    for m, cnt in sorted(methods.items(), key=lambda x: -x[1]):
        print(f"    {m:30s} : {cnt} 条")

    print("\n" + "=" * 80)
    print("  完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
