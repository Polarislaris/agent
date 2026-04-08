package com.agent.agent.model;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * DTO — deserializes the Python /api/v1/scrape-data response
 */
public class ScrapeDataResponse {

    private List<JobRow> jobs;

    @JsonProperty("job_documents")
    private List<JobDocumentRow> jobDocuments;

    public ScrapeDataResponse() {}

    public List<JobRow> getJobs() { return jobs; }
    public void setJobs(List<JobRow> jobs) { this.jobs = jobs; }

    public List<JobDocumentRow> getJobDocuments() { return jobDocuments; }
    public void setJobDocuments(List<JobDocumentRow> jobDocuments) { this.jobDocuments = jobDocuments; }

    /**
     * Represents a row in the "Jobs" table (from Python scrape)
     */
    public static class JobRow {
        @JsonProperty("job_id")
        private String jobId;

        private String company;
        private String title;
        private String location;

        @JsonProperty("apply_url")
        private String applyUrl;

        @JsonProperty("post_date")
        private String postDate;

        public JobRow() {}

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

        public String getPostDate() { return postDate; }
        public void setPostDate(String postDate) { this.postDate = postDate; }
    }

    /**
     * Represents a row in the "job_documents" table (from Python scrape)
     */
    public static class JobDocumentRow {
        @JsonProperty("job_id")
        private String jobId;

        @JsonProperty("fetch_url")
        private String fetchUrl;

        @JsonProperty("scrape_method")
        private String scrapeMethod;

        @JsonProperty("jd_raw_text")
        private String jdRawText;

        public JobDocumentRow() {}

        public String getJobId() { return jobId; }
        public void setJobId(String jobId) { this.jobId = jobId; }

        public String getFetchUrl() { return fetchUrl; }
        public void setFetchUrl(String fetchUrl) { this.fetchUrl = fetchUrl; }

        public String getScrapeMethod() { return scrapeMethod; }
        public void setScrapeMethod(String scrapeMethod) { this.scrapeMethod = scrapeMethod; }

        public String getJdRawText() { return jdRawText; }
        public void setJdRawText(String jdRawText) { this.jdRawText = jdRawText; }
    }
}
