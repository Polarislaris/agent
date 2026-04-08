package com.agent.agent.repository;

import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import com.agent.agent.model.JobEntity;

@Repository
public interface JobRepository extends JpaRepository<JobEntity, String> {

    /**
     * 根据公司名称和岗位名称查找已有记录（用于去重）
     */
    Optional<JobEntity> findByCompanyAndTitle(String company, String title);

    /**
     * 检查是否存在相同公司和岗位名称的记录
     */
    boolean existsByCompanyAndTitle(String company, String title);
}
