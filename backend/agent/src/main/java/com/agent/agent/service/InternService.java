package com.agent.agent.service;

import java.util.List;
import java.util.Optional;
import java.util.logging.Logger;

import org.springframework.stereotype.Service;

import com.agent.agent.model.InternPost;

/**
 * InternService — 直接透传给 Python FastAPI，不在 Java 侧缓存。
 * Python 已有 24h TTL 的内存缓存，Java 无需重复缓存。
 * 这样 AI 后台充实完成后，前端下次请求即可拿到最新数据。
 */
@Service
public class InternService {

    private static final Logger LOG = Logger.getLogger(InternService.class.getName());

    private final PythonDataClient pythonClient;

    public InternService(PythonDataClient pythonClient) {
        this.pythonClient = pythonClient;
    }

    public List<InternPost> getAllPosts() {
        List<InternPost> posts = pythonClient.fetchAllInterns();
        LOG.info("getAllPosts: returning " + posts.size() + " posts from Python");
        return posts;
    }

    public Optional<InternPost> getPostById(String id) {
        return pythonClient.fetchAllInterns()
                .stream()
                .filter(p -> id.equals(p.getId()))
                .findFirst();
    }

    /** 触发 Python 侧强制重新抓取（绕过 24h 缓存，重新爬取 + AI 充实） */
    public void refreshData() {
        pythonClient.forceRefresh();
    }
}
