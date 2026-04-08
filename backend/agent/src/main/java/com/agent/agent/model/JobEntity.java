package com.agent.agent.model;

import java.time.LocalDate;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/**
 * JPA Entity — maps to Supabase "Jobs" table
 */
@Entity
@Table(name = "\"Jobs\"")
public class JobEntity {

    @Id
    @Column(name = "job_id", nullable = false)
    private String jobId;

    @Column(name = "company")
    private String company;

    @Column(name = "title")
    private String title;

    @Column(name = "location")
    private String location;

    @Column(name = "apply_url")
    private String applyUrl;

    @Column(name = "post_date")
    private LocalDate postDate;

    public JobEntity() {}

    public JobEntity(String jobId, String company, String title,
                     String location, String applyUrl, LocalDate postDate) {
        this.jobId = jobId;
        this.company = company;
        this.title = title;
        this.location = location;
        this.applyUrl = applyUrl;
        this.postDate = postDate;
    }

    public String getJobId() { return jobId; }
    public void setJobId(String jobId) { this.jobId = jobId; }

    public String getCompany() { return company; }
    public void setCompany(String company) { this.company = company; }

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }

    public String getLocation() { return location; }
    public void setLocation(String location) { this.location = location; }

    public String getApplyUrl() { return applyUrl; }
    public void setApplyUrl(String applyUrl) { this.applyUrl = applyUrl; }

    public LocalDate getPostDate() { return postDate; }
    public void setPostDate(LocalDate postDate) { this.postDate = postDate; }
}
