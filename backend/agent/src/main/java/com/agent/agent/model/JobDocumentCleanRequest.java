package com.agent.agent.model;

import java.util.ArrayList;
import java.util.List;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Request body for Python /api/v1/clean-job-documents
 */
public class JobDocumentCleanRequest {

    @JsonProperty("documents")
    private List<DocumentItem> documents = new ArrayList<>();

    @JsonProperty("min_length")
    private int minLength = 50;

    public JobDocumentCleanRequest() {}

    public JobDocumentCleanRequest(List<DocumentItem> documents, int minLength) {
        this.documents = documents;
        this.minLength = minLength;
    }

    public List<DocumentItem> getDocuments() { return documents; }
    public void setDocuments(List<DocumentItem> documents) { this.documents = documents; }

    public int getMinLength() { return minLength; }
    public void setMinLength(int minLength) { this.minLength = minLength; }

    public static class DocumentItem {
        @JsonProperty("job_id")
        private String jobId;

        @JsonProperty("jd_raw_text")
        private String jdRawText;

        public DocumentItem() {}

        public DocumentItem(String jobId, String jdRawText) {
            this.jobId = jobId;
            this.jdRawText = jdRawText;
        }

        public String getJobId() { return jobId; }
        public void setJobId(String jobId) { this.jobId = jobId; }

        public String getJdRawText() { return jdRawText; }
        public void setJdRawText(String jdRawText) { this.jdRawText = jdRawText; }
    }
}
