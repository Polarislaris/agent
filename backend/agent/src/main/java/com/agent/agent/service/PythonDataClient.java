package com.agent.agent.service;

import java.time.Duration;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.Collections;
import java.util.List;
import java.util.logging.Level;
import java.util.logging.Logger;

import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import com.agent.agent.model.InternPost;
import com.agent.agent.model.JobDocumentCleanRequest;
import com.agent.agent.model.JobDocumentCleanResponse;
import com.agent.agent.model.ScrapeDataResponse;
import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * 调用 Python FastAPI (http://localhost:8000) 获取实习数据
 */
@Service
public class PythonDataClient {

    private static final Logger LOG = Logger.getLogger(PythonDataClient.class.getName());
    private static final String PYTHON_BASE_URL = "http://localhost:8000/api/v1";

    private final RestTemplate rest;
    private final ObjectMapper objectMapper = new ObjectMapper();
        private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .version(HttpClient.Version.HTTP_1_1)
            .build();

    public PythonDataClient(RestTemplateBuilder builder) {
        this.rest = builder
                .setConnectTimeout(Duration.ofSeconds(10))
                .setReadTimeout(Duration.ofSeconds(600))  // scrape-data fetches ~100 apply pages, can take 5+ mins
                .build();
    }

    /**
     * 从 Python 端拉取全部实习岗位
     * @return 岗位列表；网络异常时返回空列表
     */
    public List<InternPost> fetchAllInterns() {
        try {
            ResponseEntity<List<InternPost>> resp = rest.exchange(
                    PYTHON_BASE_URL + "/interns",
                    HttpMethod.GET,
                    null,
                    new ParameterizedTypeReference<List<InternPost>>() {}
            );
            List<InternPost> body = resp.getBody();
            LOG.info("Fetched " + (body == null ? 0 : body.size()) + " posts from Python service");
            return body != null ? body : Collections.emptyList();
        } catch (Exception e) {
            LOG.log(Level.WARNING, "Python service unreachable: " + e.getMessage());
            return Collections.emptyList();
        }
    }

    /**
     * 调用 Python /api/v1/scrape-data — 爬取 README + apply pages，返回 DB-ready 数据
     * @return ScrapeDataResponse 包含 jobs 和 job_documents
     */
    public ScrapeDataResponse fetchScrapeData() {
        try {
            ResponseEntity<ScrapeDataResponse> resp = rest.postForEntity(
                    PYTHON_BASE_URL + "/scrape-data",
                    null,
                    ScrapeDataResponse.class
            );
            ScrapeDataResponse body = resp.getBody();
            LOG.info("Fetched scrape-data: " +
                    (body != null && body.getJobs() != null ? body.getJobs().size() : 0) + " jobs, " +
                    (body != null && body.getJobDocuments() != null ? body.getJobDocuments().size() : 0) + " documents");
            return body;
        } catch (Exception e) {
            LOG.log(Level.WARNING, "Python scrape-data failed: " + e.getMessage());
            return null;
        }
    }

    /**
     * 调用 Python /api/v1/clean-job-documents
     * 输入：job_id + jd_raw_text
     * 输出：jd_clean_text / jd_clean_hash / delete_row
     */
    public JobDocumentCleanResponse cleanJobDocuments(
            List<JobDocumentCleanRequest.DocumentItem> documents,
            int minLength
    ) {
        try {
            JobDocumentCleanRequest payload = new JobDocumentCleanRequest(documents, minLength);
            String jsonPayload = objectMapper.writeValueAsString(payload);

            HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(PYTHON_BASE_URL + "/clean-job-documents"))
                    .version(HttpClient.Version.HTTP_1_1)
                .timeout(Duration.ofSeconds(600))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(jsonPayload))
                .build();

            HttpResponse<String> response = httpClient.send(
                request,
                HttpResponse.BodyHandlers.ofString()
            );

            if (response.statusCode() < 200 || response.statusCode() >= 300) {
            LOG.warning("Python clean-job-documents failed with status " + response.statusCode() + ": " + response.body());
            return null;
            }

            JobDocumentCleanResponse body = objectMapper.readValue(response.body(), JobDocumentCleanResponse.class);
            LOG.info("Fetched clean-job-documents: " +
                    (body != null ? body.getTotal() : 0) + " rows, " +
                    (body != null ? body.getDeleteCount() : 0) + " to delete");
            return body;
        } catch (Exception e) {
            LOG.log(Level.WARNING, "Python clean-job-documents failed: " + e.getMessage());
            return null;
        }
    }

    /**
     * 调用 Python 侧强制刷新接口（绕过 24h 缓存，重新抓取 + AI 充实）
     */
    public void forceRefresh() {
        try {
            rest.postForEntity(PYTHON_BASE_URL + "/interns/refresh", null, String.class);
            LOG.info("Python force-refresh triggered");
        } catch (Exception e) {
            LOG.log(Level.WARNING, "Python force-refresh failed: " + e.getMessage());
        }
    }

    /**
     * 健康检查：检测 Python 服务是否可用
     * @return true = Python 服务已就绪；false = 不可用
     */
    public boolean isPythonServiceReady() {
        try {
            ResponseEntity<String> resp = rest.getForEntity(
                    "http://localhost:8000/health", String.class);
            return resp.getStatusCode().is2xxSuccessful();
        } catch (Exception e) {
            return false;
        }
    }
}
