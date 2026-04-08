package com.agent.agent.service;

import java.util.logging.Logger;

import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

/**
 * StartupDataInitializer — 应用启动后自动检查数据库状态
 *
 * 逻辑：
 * 1. 等待 Python 服务就绪（最多 60 秒，每 3 秒重试）
 * 2. 如果 Jobs 和 job_documents 表都为空 → 程序首次启动，自动爬取15天内的岗位数据
 * 3. 如果表不为空 → 已有数据，跳过初始化爬取
 * 4. 如果 Python 服务不可用 → 记录错误，可通过 /api/interns/db/init 手动重试
 */
@Component
public class StartupDataInitializer {

    private static final Logger LOG = Logger.getLogger(StartupDataInitializer.class.getName());

    /** Python 服务就绪等待：最多等 60 秒 */
    private static final int PYTHON_READY_MAX_WAIT_SECONDS = 60;
    /** 每次检测间隔 3 秒 */
    private static final int PYTHON_READY_POLL_INTERVAL = 3;
    /** 爬取失败最大重试次数 */
    private static final int SCRAPE_MAX_RETRIES = 3;
    /** 重试间隔 10 秒 */
    private static final int SCRAPE_RETRY_DELAY_SECONDS = 10;

    private final JobDataService jobDataService;
    private final PythonDataClient pythonClient;

    /** 初始化状态，供 Controller 查询 */
    private volatile String initStatus = "pending";
    private volatile String initMessage = "尚未开始检查";

    public StartupDataInitializer(JobDataService jobDataService, PythonDataClient pythonClient) {
        this.jobDataService = jobDataService;
        this.pythonClient = pythonClient;
    }

    @Async
    @EventListener(ApplicationReadyEvent.class)
    public void onApplicationReady() {
        LOG.info("=== [启动检测] 开始检查数据库初始化状态 ===");
        initStatus = "checking";
        initMessage = "正在检查 Python 服务和数据库状态...";

        // ── Step 1: 等待 Python 服务就绪 ────────────────────────
        if (!waitForPythonService()) {
            initStatus = "error";
            initMessage = "Python 服务 (localhost:8000) 不可用，初始化爬取已跳过。可通过 POST /api/interns/db/init 手动触发。";
            LOG.severe("[启动检测] " + initMessage);
            return;
        }

        // ── Step 2: 检查数据库是否为空 ─────────────────────────
        if (jobDataService.isDatabaseEmpty()) {
            LOG.info("[启动检测] 数据库为空，判定为首次启动，开始自动爬取15天内的岗位数据...");
            initStatus = "scraping";
            initMessage = "数据库为空，正在自动爬取数据...";

            // ── Step 3: 带重试的爬取 ────────────────────────────
            scrapeWithRetry();
        } else {
            long jobCount = jobDataService.getJobCount();
            long docCount = jobDataService.getJobDocumentCount();
            initStatus = "skipped";
            initMessage = "数据库已有数据 (Jobs=" + jobCount + ", Documents=" + docCount + ")，跳过初始化爬取";
            LOG.info("[启动检测] " + initMessage);
        }
    }

    /**
     * 手动触发初始化爬取（供 Controller 调用）
     * @return 保存的岗位数量
     */
    public int manualInitialize() {
        LOG.info("=== [手动触发] 开始初始化爬取 ===");

        if (!pythonClient.isPythonServiceReady()) {
            initStatus = "error";
            initMessage = "Python 服务不可用，无法执行爬取";
            throw new RuntimeException(initMessage);
        }

        initStatus = "scraping";
        initMessage = "手动触发爬取中...";

        try {
            int saved = jobDataService.initializeScrape();
            initStatus = "done";
            initMessage = "手动爬取完成，共保存 " + saved + " 个岗位";
            LOG.info("[手动触发] " + initMessage);
            return saved;
        } catch (Exception e) {
            initStatus = "error";
            initMessage = "手动爬取失败: " + e.getMessage();
            LOG.severe("[手动触发] " + initMessage);
            throw e;
        }
    }

    /** 获取初始化状态 */
    public String getInitStatus() { return initStatus; }
    /** 获取初始化消息 */
    public String getInitMessage() { return initMessage; }

    // ───────────────────────── 内部方法 ──────────────────────────

    /**
     * 轮询等待 Python 服务就绪
     */
    private boolean waitForPythonService() {
        int waited = 0;
        while (waited < PYTHON_READY_MAX_WAIT_SECONDS) {
            if (pythonClient.isPythonServiceReady()) {
                LOG.info("[启动检测] Python 服务已就绪 (等待了 " + waited + " 秒)");
                return true;
            }
            LOG.info("[启动检测] 等待 Python 服务启动... (" + waited + "/" + PYTHON_READY_MAX_WAIT_SECONDS + "s)");
            try {
                Thread.sleep(PYTHON_READY_POLL_INTERVAL * 1000L);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return false;
            }
            waited += PYTHON_READY_POLL_INTERVAL;
        }
        LOG.warning("[启动检测] 等待 Python 服务超时 (" + PYTHON_READY_MAX_WAIT_SECONDS + "s)");
        return false;
    }

    /**
     * 带重试机制的爬取
     */
    private void scrapeWithRetry() {
        for (int attempt = 1; attempt <= SCRAPE_MAX_RETRIES; attempt++) {
            try {
                LOG.info("[启动检测] 第 " + attempt + "/" + SCRAPE_MAX_RETRIES + " 次尝试爬取...");
                int saved = jobDataService.initializeScrape();
                initStatus = "done";
                initMessage = "初始化爬取完成，共保存 " + saved + " 个岗位到数据库";
                LOG.info("[启动检测] ✓ " + initMessage);
                return;
            } catch (Exception e) {
                LOG.warning("[启动检测] 第 " + attempt + " 次爬取失败: " + e.getMessage());
                if (attempt < SCRAPE_MAX_RETRIES) {
                    LOG.info("[启动检测] " + SCRAPE_RETRY_DELAY_SECONDS + " 秒后重试...");
                    try {
                        Thread.sleep(SCRAPE_RETRY_DELAY_SECONDS * 1000L);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
            }
        }
        initStatus = "error";
        initMessage = "初始化爬取失败（已重试 " + SCRAPE_MAX_RETRIES + " 次）。可通过 POST /api/interns/db/init 手动重试。";
        LOG.severe("[启动检测] " + initMessage);
    }
}
