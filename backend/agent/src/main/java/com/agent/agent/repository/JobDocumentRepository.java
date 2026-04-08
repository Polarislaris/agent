package com.agent.agent.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import com.agent.agent.model.JobDocumentEntity;

@Repository
public interface JobDocumentRepository extends JpaRepository<JobDocumentEntity, String> {
}
