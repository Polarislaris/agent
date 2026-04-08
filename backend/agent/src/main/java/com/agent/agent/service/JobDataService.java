package com.agent.agent.service;

import java.time.LocalDate;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.logging.Logger;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import com.agent.agent.model.JobDocumentCleanRequest;
import com.agent.agent.model.JobDocumentCleanResponse;
import com.agent.agent.model.JobDocumentEntity;
import com.agent.agent.model.JobEntity;
import com.agent.agent.model.ScrapeDataResponse;
import com.agent.agent.repository.JobDocumentRepository;
import com.agent.agent.repository.JobRepository;

/**
 * JobDataService — 负责从 Python 拉取爬虫数据并写入 Supabase (Jobs + job_documents)
 *
 * 使用 JdbcTemplate + INSERT ... ON CONFLICT 原生 SQL 写入，
 * 每条 INSERT 只有一次网络 round-trip。
 * 如果出现连续 statement_timeout / 连接异常，自动终止当前批次避免卡死。
 */
@Service
public class JobDataService {

    private static final Logger LOG = Logger.getLogger(JobDataService.class.getName());

    /** 连续失败达到此阈值则终止整个批次，避免卡死 */
    private static final int MAX_CONSECUTIVE_FAILURES = 3;

    /** 每条 Jobs INSERT 之间的间隔（毫秒），比 Documents 更大以避免索引锁竞争 */
    private static final long JOB_INSERT_DELAY_MS = 500;

    /** 每条 Documents INSERT 之间的间隔（毫秒） */
    private static final long DOC_INSERT_DELAY_MS = 200;

    /** 单条 SQL 查询超时秒数（防止 Supabase statement_timeout 导致长时间等待） */
    private static final int QUERY_TIMEOUT_SECONDS = 15;

    /** 单条 INSERT 失败后重试延迟（毫秒） */
    private static final long RETRY_DELAY_MS = 3000;

    /** 判断字符串是否为空（null 或空白） */
    private static boolean isBlank(String s) {
        return s == null || s.trim().isEmpty();
    }

    /* ── 原生 SQL ── */
    /** 普通 INSERT（不使用 ON CONFLICT，避免索引锁竞争） */
    private static final String INSERT_JOB_SQL =
            "INSERT INTO \"Jobs\" (job_id, company, title, location, apply_url, post_date) " +
            "VALUES (?, ?, ?, ?, ?, ?)";

    /** 检查 job_id 是否已存在 */
    private static final String CHECK_JOB_ID_SQL =
            "SELECT EXISTS(SELECT 1 FROM \"Jobs\" WHERE job_id = ?)";

    private static final String INSERT_DOC_SQL =
            "INSERT INTO job_documents (job_id, fetch_url, scrape_method, jd_raw_text) " +
            "VALUES (?, ?, ?, ?) " +
            "ON CONFLICT (job_id) DO NOTHING";

        /** 清洗链路：读取待清洗数据 */
        private static final String SELECT_DOCS_FOR_CLEAN_SQL =
            "SELECT job_id, jd_raw_text FROM job_documents " +
            "WHERE jd_raw_text IS NOT NULL AND btrim(jd_raw_text) <> '' " +
            "ORDER BY job_id";

        /** 清洗链路：写回 jd_clean_text / jd_clean_hash */
        private static final String UPDATE_DOC_CLEAN_SQL =
            "UPDATE job_documents SET jd_clean_text = ?, jd_clean_hash = ? WHERE job_id = ?";

        /** 清洗链路：清洗后太短则删除 */
        private static final String DELETE_DOC_SQL =
            "DELETE FROM job_documents WHERE job_id = ?";

    /** 按 company+title+location 去重：同公司同职位同地点视为重复（location 为空时视为相同） */
    private static final String CHECK_DUPLICATE_SQL =
            "SELECT EXISTS(SELECT 1 FROM \"Jobs\" WHERE lower(trim(company))=lower(trim(?)) AND lower(trim(title))=lower(trim(?)) AND coalesce(lower(trim(location)),'')=coalesce(lower(trim(?)),'' ))";

    private final PythonDataClient pythonClient;
    private final JobRepository jobRepository;
    private final JobDocumentRepository jobDocumentRepository;
    private final JdbcTemplate jdbc;

    public JobDataService(PythonDataClient pythonClient,
                          JobRepository jobRepository,
                          JobDocumentRepository jobDocumentRepository,
                          JdbcTemplate jdbcTemplate) {
        this.pythonClient = pythonClient;
        this.jobRepository = jobRepository;
        this.jobDocumentRepository = jobDocumentRepository;
        this.jdbc = jdbcTemplate;
    }

    /* ============================================================
     *  数据库状态检查
     * ============================================================ */

    public boolean isDatabaseEmpty() {
        long jobCount = jobRepository.count();
        long docCount = jobDocumentRepository.count();
        LOG.info("Database status: Jobs=" + jobCount + ", job_documents=" + docCount);
        return jobCount == 0 && docCount == 0;
    }

    public long getJobCount()         { return jobRepository.count(); }
    public long getJobDocumentCount() { return jobDocumentRepository.count(); }

    /* ============================================================
     *  爬取入口
     * ============================================================ */

    /** 初始化爬取：数据库为空时自动调用 */
    public int initializeScrape() {
        LOG.info("=== 数据库为空，开始初始化爬取15天内的岗位数据 ===");
        ScrapeDataResponse data = pythonClient.fetchScrapeData();
        if (data == null || data.getJobs() == null || data.getJobs().isEmpty()) {
            LOG.warning("Python scrape-data returned empty during initialization");
            return 0;
        }
        int saved = saveFromPythonResponse(data);
        LOG.info("=== 初始化爬取完成，共保存 " + saved + " 个岗位 ===");
        return saved;
    }

    /** 手动触发全量爬取 */
    public int scrapeAndSave() {
        LOG.info("Calling Python /api/v1/scrape-data ...");
        ScrapeDataResponse data = pythonClient.fetchScrapeData();
        if (data == null || data.getJobs() == null || data.getJobs().isEmpty()) {
            LOG.warning("Python scrape-data returned empty, nothing to save");
            return 0;
        }
        return saveFromPythonResponse(data);
    }

    /* ============================================================
     *  核心写入逻辑 — 原生 SQL，每条独立，不会超时
     * ============================================================ */

    /**
     * 将 Python 返回的数据逐条写入 Supabase。
     * - 使用原生 INSERT ... ON CONFLICT DO NOTHING（单条 SQL，一次网络 RT）
     * - company+title 相同视为重复，跳过
     * - 每写 10 条打一次日志
     * - 单条失败直接丢弃，连续失败超过阈值则终止批次
     */
    public int saveFromPythonResponse(ScrapeDataResponse data) {
        List<ScrapeDataResponse.JobRow> jobRows = data.getJobs();
        List<ScrapeDataResponse.JobDocumentRow> docRows = data.getJobDocuments();

        LOG.info("Received " + jobRows.size() + " jobs, "
                + (docRows != null ? docRows.size() : 0) + " documents from Python");

        // 设置查询超时，防止单条 SQL 卡住太久
        jdbc.setQueryTimeout(QUERY_TIMEOUT_SECONDS);

        // ── 写入 Jobs ──────────────────────────────────────────────
        int savedJobs = 0, skippedJobs = 0, failedJobs = 0;
        int consecutiveFailures = 0;

        int discardedJobs = 0;

        for (ScrapeDataResponse.JobRow row : jobRows) {
            // 连续失败保护：防止卡死
            if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
                LOG.severe("连续 " + MAX_CONSECUTIVE_FAILURES + " 条写入失败（可能是 statement_timeout / 网络问题），终止本批次 Jobs 写入");
                break;
            }

            // ── 空值校验：只有 location 允许为空，其余字段为空则丢弃 ──
            if (isBlank(row.getJobId()) || isBlank(row.getCompany()) || isBlank(row.getTitle())
                    || isBlank(row.getApplyUrl()) || isBlank(row.getPostDate())) {
                discardedJobs++;
                LOG.info("丢弃 Job（关键字段为空）: job_id=" + row.getJobId()
                        + ", company=" + row.getCompany() + ", title=" + row.getTitle()
                        + ", apply_url=" + (isBlank(row.getApplyUrl()) ? "[空]" : "ok")
                        + ", post_date=" + (isBlank(row.getPostDate()) ? "[空]" : "ok"));
                continue;
            }

            try {
                // 先检查 job_id 是否已存在（SELECT 比 ON CONFLICT 更轻量，不需要索引写锁）
                Boolean idExists = jdbc.queryForObject(CHECK_JOB_ID_SQL, Boolean.class, row.getJobId());
                if (Boolean.TRUE.equals(idExists)) {
                    skippedJobs++;
                    consecutiveFailures = 0;
                    continue;
                }

                // company+title+location 去重
                if (row.getCompany() != null && row.getTitle() != null) {
                    Boolean exists = jdbc.queryForObject(CHECK_DUPLICATE_SQL, Boolean.class,
                            row.getCompany(), row.getTitle(), row.getLocation());
                    if (Boolean.TRUE.equals(exists)) {
                        skippedJobs++;
                        consecutiveFailures = 0;
                        continue;
                    }
                }

                LocalDate postDate = null;
                if (row.getPostDate() != null && !row.getPostDate().isEmpty()) {
                    postDate = LocalDate.parse(row.getPostDate());
                }

                // 普通 INSERT（不使用 ON CONFLICT，避免索引锁竞争）+ 单条重试
                boolean inserted = false;
                for (int attempt = 1; attempt <= 2; attempt++) {
                    try {
                        int affected = jdbc.update(INSERT_JOB_SQL,
                                row.getJobId(), row.getCompany(), row.getTitle(),
                                row.getLocation(), row.getApplyUrl(), postDate);
                        if (affected > 0) {
                            savedJobs++;
                            if (savedJobs % 10 == 0) {
                                LOG.info("已写入 " + savedJobs + " 条 job ...");
                            }
                        }
                        inserted = true;
                        break; // 成功，退出重试
                    } catch (Exception insertEx) {
                        if (attempt == 1) {
                            LOG.info("Job " + row.getJobId() + " INSERT 第1次失败，" + (RETRY_DELAY_MS / 1000) + "s 后重试: " + insertEx.getMessage());
                            Thread.sleep(RETRY_DELAY_MS);
                        } else {
                            throw insertEx; // 第二次还失败，抛出让外层处理
                        }
                    }
                }

                if (inserted) {
                    consecutiveFailures = 0;
                }

                // 写入间隔 — Jobs 表间隔更大
                Thread.sleep(JOB_INSERT_DELAY_MS);

            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
                LOG.warning("写入被中断");
                break;
            } catch (Exception e) {
                failedJobs++;
                consecutiveFailures++;
                LOG.warning("丢弃 job " + row.getJobId() + " (连续失败 " + consecutiveFailures + "): " + e.getMessage());
            }
        }
        LOG.info("Jobs 完成: saved=" + savedJobs + ", skipped(duplicate)=" + skippedJobs
                + ", discarded(null)=" + discardedJobs + ", failed(error)=" + failedJobs);

        // ── 写入 job_documents ─────────────────────────────────────
        int savedDocs = 0, failedDocs = 0;
        consecutiveFailures = 0;

        int discardedDocs = 0;

        if (docRows != null) {
            for (ScrapeDataResponse.JobDocumentRow row : docRows) {
                if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
                    LOG.severe("连续 " + MAX_CONSECUTIVE_FAILURES + " 条 document 写入失败，终止本批次 Documents 写入");
                    break;
                }

                // ── 空值校验：job_id / fetch_url / scrape_method / jd_raw_text 都不可为空 ──
                if (isBlank(row.getJobId()) || isBlank(row.getFetchUrl())
                        || isBlank(row.getScrapeMethod()) || isBlank(row.getJdRawText())) {
                    discardedDocs++;
                    LOG.info("丢弃 Document（关键字段为空）: job_id=" + row.getJobId()
                            + ", fetch_url=" + (isBlank(row.getFetchUrl()) ? "[空]" : "ok")
                            + ", scrape_method=" + (isBlank(row.getScrapeMethod()) ? "[空]" : "ok")
                            + ", jd_raw_text=" + (isBlank(row.getJdRawText()) ? "[空]" : "ok"));
                    continue;
                }

                try {
                    int affected = jdbc.update(INSERT_DOC_SQL,
                            row.getJobId(), row.getFetchUrl(),
                            row.getScrapeMethod(), row.getJdRawText());

                    if (affected > 0) {
                        savedDocs++;
                        if (savedDocs % 10 == 0) {
                            LOG.info("已写入 " + savedDocs + " 条 document ...");
                        }
                    }
                    consecutiveFailures = 0;

                    Thread.sleep(DOC_INSERT_DELAY_MS);

                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    LOG.warning("Document 写入被中断");
                    break;
                } catch (Exception e) {
                    failedDocs++;
                    consecutiveFailures++;
                    LOG.warning("丢弃 document " + row.getJobId() + " (连续失败 " + consecutiveFailures + "): " + e.getMessage());
                }
            }
        }
        LOG.info("Documents 完成: saved=" + savedDocs + ", discarded(null)=" + discardedDocs + ", failed(error)=" + failedDocs);
        return savedJobs;
    }

    /* ============================================================
     *  查询（仍用 JPA Repository，读取不受 timeout 影响）
     * ============================================================ */

    public List<JobEntity> getAllJobs() {
        return jobRepository.findAll();
    }

    public List<JobDocumentEntity> getAllJobDocuments() {
        return jobDocumentRepository.findAll();
    }

    /**
     * Java 从数据库读取 jd_raw_text，调用 Python 清洗，再由 Java 回写数据库。
     */
    public Map<String, Object> cleanJobDocumentsViaPython(int minLength, int limit) {
        int effectiveMinLength = minLength > 0 ? minLength : 50;
        int effectiveLimit = Math.max(limit, 0);

        String selectSql = SELECT_DOCS_FOR_CLEAN_SQL;
        List<JobDocumentCleanRequest.DocumentItem> documents;

        if (effectiveLimit > 0) {
            selectSql += " LIMIT ?";
            documents = jdbc.query(
                    selectSql,
                    (rs, rowNum) -> new JobDocumentCleanRequest.DocumentItem(
                            rs.getString("job_id"),
                            rs.getString("jd_raw_text")
                    ),
                    effectiveLimit
            );
        } else {
            documents = jdbc.query(
                    selectSql,
                    (rs, rowNum) -> new JobDocumentCleanRequest.DocumentItem(
                            rs.getString("job_id"),
                            rs.getString("jd_raw_text")
                    )
            );
        }

        if (documents.isEmpty()) {
            Map<String, Object> emptyResult = new HashMap<>();
            emptyResult.put("status", "ok");
            emptyResult.put("message", "No job_documents with jd_raw_text to clean");
            emptyResult.put("scanned", 0);
            emptyResult.put("updated", 0);
            emptyResult.put("deleted", 0);
            return emptyResult;
        }

        JobDocumentCleanResponse cleaned = pythonClient.cleanJobDocuments(documents, effectiveMinLength);
        if (cleaned == null || cleaned.getResults() == null) {
            Map<String, Object> failed = new HashMap<>();
            failed.put("status", "error");
            failed.put("message", "Python cleaning service returned null");
            failed.put("scanned", documents.size());
            failed.put("updated", 0);
            failed.put("deleted", 0);
            return failed;
        }

        int updatedRows = 0;
        int deletedRows = 0;

        for (JobDocumentCleanResponse.ResultItem row : cleaned.getResults()) {
            if (row.isDeleteRow()) {
                deletedRows += jdbc.update(DELETE_DOC_SQL, row.getJobId());
            } else {
                updatedRows += jdbc.update(
                        UPDATE_DOC_CLEAN_SQL,
                        row.getJdCleanText(),
                        row.getJdCleanHash(),
                        row.getJobId()
                );
            }
        }

        Map<String, Object> result = new HashMap<>();
        result.put("status", "ok");
        result.put("min_length", effectiveMinLength);
        result.put("scanned", documents.size());
        result.put("python_total", cleaned.getTotal());
        result.put("python_delete_count", cleaned.getDeleteCount());
        result.put("python_keep_count", cleaned.getKeepCount());
        result.put("updated", updatedRows);
        result.put("deleted", deletedRows);
        return result;
    }
}
