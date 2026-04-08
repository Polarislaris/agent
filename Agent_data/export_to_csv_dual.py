#!/usr/bin/env python3
"""
导出 Python 爬虫数据为两个关联 CSV 文件 —— 对应 Java 写入数据库的两个表

导出文件：
1. jobs.csv - 对应 Jobs 表（job_id, company, title, location, apply_url, post_date）
2. job_documentation.csv - 对应 job_documents 表（job_id, fetch_url, scrape_method, jd_raw_text）

特点：
- 两个文件行数相同（除去 header）
- 通过 job_id 一一对应
- 所有必需字段校验通过
- 可直接用于测试 Java 接口写入数据库的流程
"""

import csv
import sys
from pathlib import Path
from datetime import datetime

# 引入 scraper 模块
sys.path.insert(0, str(Path(__file__).parent / "app"))
from scraper import scrape_for_db_sync

def main():
    print("=" * 100)
    print("导出爬虫数据为两个关联 CSV 文件（Jobs & job_documents）")
    print("=" * 100)
    print()
    
    # 获取爬虫数据
    print("[1/4] 正在调用 Python 爬虫获取数据...")
    try:
        data = scrape_for_db_sync(limit=999)
    except Exception as e:
        print(f"✗ 爬虫错误: {e}")
        return 1
    
    jobs = data.get("jobs", [])
    documents = data.get("job_documents", [])
    
    if not jobs or not documents:
        print("✗ 爬虫返回空数据")
        return 1
    
    print(f"✓ Jobs: {len(jobs)} 条")
    print(f"✓ Documents: {len(documents)} 条")
    print()
    
    # 验证两个列表行数是否对应
    print("[2/4] 验证数据一致性...")
    if len(jobs) != len(documents):
        print(f"✗ 错误：Jobs ({len(jobs)}) 和 Documents ({len(documents)}) 行数不匹配！")
        return 1
    print(f"✓ Jobs 和 Documents 一一对应（共 {len(jobs)} 条）")
    
    # 验证 job_id 映射
    job_ids_in_jobs = {j["job_id"] for j in jobs}
    job_ids_in_docs = {d["job_id"] for d in documents}
    
    if job_ids_in_jobs != job_ids_in_docs:
        print(f"✗ 错误：job_id 集合不相同！")
        print(f"  Jobs 独有: {job_ids_in_jobs - job_ids_in_docs}")
        print(f"  Documents 独有: {job_ids_in_docs - job_ids_in_jobs}")
        return 1
    print(f"✓ 所有 job_id 一一对应")
    print()
    
    # 检查必需字段完整性
    print("[3/4] 检查必需字段...")
    jobs_issues = []
    for job in jobs:
        missing = []
        if not job.get("job_id", "").strip():
            missing.append("job_id")
        if not job.get("company", "").strip():
            missing.append("company")
        if not job.get("title", "").strip():
            missing.append("title")
        if not job.get("apply_url", "").strip():
            missing.append("apply_url")
        if not job.get("post_date", "").strip():
            missing.append("post_date")
        if missing:
            jobs_issues.append((job.get("job_id", "?"), missing))
    
    docs_issues = []
    for doc in documents:
        missing = []
        if not doc.get("job_id", "").strip():
            missing.append("job_id")
        if not doc.get("fetch_url", "").strip():
            missing.append("fetch_url")
        if not doc.get("scrape_method", "").strip():
            missing.append("scrape_method")
        if not doc.get("jd_raw_text", "").strip():
            missing.append("jd_raw_text")
        if missing:
            docs_issues.append((doc.get("job_id", "?"), missing))
    
    if jobs_issues:
        print(f"✗ Jobs 字段缺失: {len(jobs_issues)} 条")
        for job_id, missing in jobs_issues[:5]:
            print(f"  {job_id}: {missing}")
    else:
        print(f"✓ Jobs 表：所有必需字段完整")
    
    if docs_issues:
        print(f"✗ Documents 字段缺失: {len(docs_issues)} 条")
        for job_id, missing in docs_issues[:5]:
            print(f"  {job_id}: {missing}")
    else:
        print(f"✓ Documents 表：所有必需字段完整")
    
    if jobs_issues or docs_issues:
        print("\n⚠ 存在字段缺失，将只导出完整行")
    print()
    
    # 导出为 CSV
    print("[4/4] 导出为 CSV 文件...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    jobs_file = Path(__file__).parent / f"jobs_{timestamp}.csv"
    docs_file = Path(__file__).parent / f"job_documentation_{timestamp}.csv"
    
    try:
        # 导出 Jobs
        with open(jobs_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['job_id', 'company', 'title', 'location', 'apply_url', 'post_date'],
                extrasaction='ignore'
            )
            writer.writeheader()
            writer.writerows(jobs)
        
        print(f"✓ jobs_{timestamp}.csv 已保存")
        print(f"  行数: {len(jobs)} (header + {len(jobs)} data)")
        print(f"  大小: {jobs_file.stat().st_size} 字节")
        
        # 导出 Documents
        with open(docs_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['job_id', 'fetch_url', 'scrape_method', 'jd_raw_text'],
                extrasaction='ignore'
            )
            writer.writeheader()
            writer.writerows(documents)
        
        print(f"✓ job_documentation_{timestamp}.csv 已保存")
        print(f"  行数: {len(documents)} (header + {len(documents)} data)")
        print(f"  大小: {docs_file.stat().st_size} 字节")
        print()
        
        # 打印摘要
        print("=" * 100)
        print("导出完成摘要")
        print("=" * 100)
        print(f"总计数据行数: {len(jobs)}")
        print()
        print(f"Jobs CSV 文件:")
        print(f"  位置: {jobs_file}")
        print(f"  列: job_id, company, title, location, apply_url, post_date")
        print()
        print(f"job_documentation CSV 文件:")
        print(f"  位置: {docs_file}")
        print(f"  列: job_id, fetch_url, scrape_method, jd_raw_text")
        print()
        print("两个文件通过 job_id 一一映射，可用于以下场景：")
        print("  1. 检查爬虫输出数据质量")
        print("  2. 测试 Java 接口写入数据库")
        print("  3. 对比数据库中已保存的内容")
        print("=" * 100)
        
        return 0
        
    except Exception as e:
        print(f"✗ 导出失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
