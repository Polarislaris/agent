package com.agent.agent.service;

import java.time.Duration;
import java.util.Arrays;
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

/**
 * 调用 Python FastAPI (http://localhost:8000) 获取实习数据
 */
@Service
public class PythonDataClient {

    private static final Logger LOG = Logger.getLogger(PythonDataClient.class.getName());
    private static final String PYTHON_BASE_URL = "http://localhost:8000/api/v1";

    private final RestTemplate rest;

    public PythonDataClient(RestTemplateBuilder builder) {
        this.rest = builder
                .setConnectTimeout(Duration.ofSeconds(10))
                .setReadTimeout(Duration.ofSeconds(60))  // First request may trigger GitHub scrape
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
            LOG.log(Level.WARNING, "Python service unreachable, will use placeholder: " + e.getMessage());
            return Collections.emptyList();
        }
    }
}
