package com.agent.agent.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/**
 * JPA Entity — maps to Supabase "job_documents" table
 */
@Entity
@Table(name = "job_documents")
public class JobDocumentEntity {

    @Id
    @Column(name = "job_id", nullable = false)
    private String jobId;

    @Column(name = "fetch_url")
    private String fetchUrl;

    @Column(name = "scrape_method")
    private String scrapeMethod;

    @Column(name = "jd_raw_text", columnDefinition = "TEXT")
    private String jdRawText;

    @Column(name = "jd_clean_text", columnDefinition = "TEXT")
    private String jdCleanText;

    @Column(name = "jd_llm_text", columnDefinition = "TEXT")
    private String jdLlmText;

    @Column(name = "jd_clean_hash")
    private String jdCleanHash;

    @Column(name = "jd_llm_hash")
    private String jdLlmHash;

    public JobDocumentEntity() {}

    public JobDocumentEntity(String jobId, String fetchUrl, String scrapeMethod, String jdRawText) {
        this.jobId = jobId;
        this.fetchUrl = fetchUrl;
        this.scrapeMethod = scrapeMethod;
        this.jdRawText = jdRawText;
    }

    public String getJobId() { return jobId; }
    public void setJobId(String jobId) { this.jobId = jobId; }

    public String getFetchUrl() { return fetchUrl; }
    public void setFetchUrl(String fetchUrl) { this.fetchUrl = fetchUrl; }

    public String getScrapeMethod() { return scrapeMethod; }
    public void setScrapeMethod(String scrapeMethod) { this.scrapeMethod = scrapeMethod; }

    public String getJdRawText() { return jdRawText; }
    public void setJdRawText(String jdRawText) { this.jdRawText = jdRawText; }

    public String getJdCleanText() { return jdCleanText; }
    public void setJdCleanText(String jdCleanText) { this.jdCleanText = jdCleanText; }

    public String getJdLlmText() { return jdLlmText; }
    public void setJdLlmText(String jdLlmText) { this.jdLlmText = jdLlmText; }

    public String getJdCleanHash() { return jdCleanHash; }
    public void setJdCleanHash(String jdCleanHash) { this.jdCleanHash = jdCleanHash; }

    public String getJdLlmHash() { return jdLlmHash; }
    public void setJdLlmHash(String jdLlmHash) { this.jdLlmHash = jdLlmHash; }
}
