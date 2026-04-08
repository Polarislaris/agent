package com.agent.agent.controller;

import java.util.List;
import java.util.Map;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.agent.agent.model.InternPost;
import com.agent.agent.model.JobDocumentEntity;
import com.agent.agent.model.JobEntity;
import com.agent.agent.model.ScrapeDataResponse;
import com.agent.agent.service.InternService;
import com.agent.agent.service.JobDataService;
import com.agent.agent.service.StartupDataInitializer;

@RestController
@RequestMapping("/api/interns")
public class InternController {

    private final InternService internService;
    private final JobDataService jobDataService;
    private final StartupDataInitializer startupInitializer;

    public InternController(InternService internService, JobDataService jobDataService,
                            StartupDataInitializer startupInitializer) {
        this.internService = internService;
        this.jobDataService = jobDataService;
        this.startupInitializer = startupInitializer;
    }

    @GetMapping
    public List<InternPost> getAllInterns() {
        return internService.getAllPosts();
    }

    @GetMapping("/{id}")
    public ResponseEntity<InternPost> getInternById(@PathVariable String id) {
        return internService.getPostById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    /** 手动触发从 Python 服务刷新数据 */
    @PostMapping("/refresh")
    public Map<String, Object> refreshData() {
        internService.refreshData();
        return Map.of("status", "ok", "count", internService.getAllPosts().size());
    }

    /**     * 触发 Python 爬虫 → 写入 Supabase (Jobs + job_documents)
     * POST /api/interns/scrape-and-save
     */
    @PostMapping("/scrape-and-save")
    public Map<String, Object> scrapeAndSave() {
        int saved = jobDataService.scrapeAndSave();
        return Map.of("status", "ok", "saved_jobs", saved);
    }

    /**
     * 接受外部 JSON 直接写入 Supabase（用于测试管道）
     * POST /api/interns/push-data
     * Body: { "jobs": [...], "job_documents": [...] }
     */
    @PostMapping("/push-data")
    public Map<String, Object> pushData(@RequestBody ScrapeDataResponse payload) {
        if (payload == null || payload.getJobs() == null || payload.getJobs().isEmpty()) {
            return Map.of("status", "error", "message", "empty payload");
        }
        int saved = jobDataService.saveFromPythonResponse(payload);
        return Map.of(
            "status", "ok",
            "received_jobs", payload.getJobs().size(),
            "saved_jobs", saved
        );
    }

    /**
     * Java 读 jd_raw_text -> Python 清洗 -> Java 写回 jd_clean_text/jd_clean_hash
     * POST /api/interns/clean-job-documents?minLength=50&limit=0
     */
    @PostMapping("/clean-job-documents")
    public Map<String, Object> cleanJobDocuments(
            @RequestParam(defaultValue = "50") int minLength,
            @RequestParam(defaultValue = "0") int limit
    ) {
        return jobDataService.cleanJobDocumentsViaPython(minLength, limit);
    }

    /**
     * 从 Supabase 读取所有 Jobs
     * GET /api/interns/db/jobs
     */
    @GetMapping("/db/jobs")
    public List<JobEntity> getDbJobs() {
        return jobDataService.getAllJobs();
    }

    /**
     * 从 Supabase 读取所有 job_documents
     * GET /api/interns/db/documents
     */
    @GetMapping("/db/documents")
    public List<JobDocumentEntity> getDbDocuments() {
        return jobDataService.getAllJobDocuments();
    }

    /**
     * 查询数据库状态（用于诊断和测试）
     * GET /api/interns/db/status
     */
    @GetMapping("/db/status")
    public Map<String, Object> getDbStatus() {
        long jobCount = jobDataService.getJobCount();
        long docCount = jobDataService.getJobDocumentCount();
        boolean isEmpty = jobCount == 0 && docCount == 0;
        return Map.of(
            "status", "ok",
            "jobs_count", jobCount,
            "documents_count", docCount,
            "database_empty", isEmpty,
            "init_status", startupInitializer.getInitStatus(),
            "init_message", startupInitializer.getInitMessage(),
            "message", isEmpty ? "数据库为空，需要初始化爬取" : "数据库已有数据"
        );
    }

    /**
     * 手动触发数据库初始化爬取（当自动初始化失败时使用）
     * POST /api/interns/db/init
     */
    @PostMapping("/db/init")
    public Map<String, Object> manualInit() {
        try {
            int saved = startupInitializer.manualInitialize();
            return Map.of(
                "status", "ok",
                "saved_jobs", saved,
                "message", "手动初始化完成，共保存 " + saved + " 个岗位"
            );
        } catch (Exception e) {
            return Map.of(
                "status", "error",
                "message", "手动初始化失败: " + e.getMessage()
            );
        }
    }
}
