package com.agent.agent.controller;

import java.util.List;
import java.util.Map;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.agent.agent.model.InternPost;
import com.agent.agent.service.InternService;

@RestController
@RequestMapping("/api/interns")
public class InternController {

    private final InternService internService;

    public InternController(InternService internService) {
        this.internService = internService;
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
}
