#!/usr/bin/env python3
import csv

# 计算实际行数
with open('jobs_20260220_032112.csv', 'r', encoding='utf-8') as f:
    jobs_rows = len(list(csv.DictReader(f)))

with open('job_documentation_20260220_032112.csv', 'r', encoding='utf-8') as f:
    docs_rows = len(list(csv.DictReader(f)))

print(f"jobs.csv 数据行数: {jobs_rows}")
print(f"job_documentation.csv 数据行数: {docs_rows}")
print(f"行数相等: {'✓' if jobs_rows == docs_rows else '✗'}")
print()

# 样本数据
print("=== jobs.csv 前3行数据 ===")
with open('jobs_20260220_032112.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i >= 3:
            break
        print(f"  [{i+1}] job_id={row['job_id']}, company={row['company'][:30]}, title={row['title'][:40]}")

print()
print("=== job_documentation.csv 前3行数据 ===")
with open('job_documentation_20260220_032112.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i >= 3:
            break
        jd_len = len(row['jd_raw_text'])
        print(f"  [{i+1}] job_id={row['job_id']}, method={row['scrape_method']}, jd_len={jd_len}")

print()
print("=== job_id 映射验证 ===")
jobs_ids = set()
docs_ids = set()

with open('jobs_20260220_032112.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        jobs_ids.add(row['job_id'])

with open('job_documentation_20260220_032112.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        docs_ids.add(row['job_id'])

print(f"Jobs 中的 job_id 数: {len(jobs_ids)}")
print(f"Documents 中的 job_id 数: {len(docs_ids)}")
print(f"相同 job_id: {len(jobs_ids & docs_ids)}")
print(f"完全一一对应: {'✓' if jobs_ids == docs_ids else '✗'}")
