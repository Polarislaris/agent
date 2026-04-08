package com.agent.agent.model;

import java.util.ArrayList;
import java.util.List;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Response body from Python /api/v1/clean-job-documents
 */
public class JobDocumentCleanResponse {

    @JsonProperty("results")
    private List<ResultItem> results = new ArrayList<>();

    @JsonProperty("total")
    private int total;

    @JsonProperty("keep_count")
    private int keepCount;

    @JsonProperty("delete_count")
    private int deleteCount;

    public JobDocumentCleanResponse() {}

    public List<ResultItem> getResults() { return results; }
    public void setResults(List<ResultItem> results) { this.results = results; }

    public int getTotal() { return total; }
    public void setTotal(int total) { this.total = total; }

    public int getKeepCount() { return keepCount; }
    public void setKeepCount(int keepCount) { this.keepCount = keepCount; }

    public int getDeleteCount() { return deleteCount; }
    public void setDeleteCount(int deleteCount) { this.deleteCount = deleteCount; }

    public static class ResultItem {
        @JsonProperty("job_id")
        private String jobId;

        @JsonProperty("jd_clean_text")
        private String jdCleanText;

        @JsonProperty("jd_clean_hash")
        private String jdCleanHash;

        @JsonProperty("delete_row")
        private boolean deleteRow;

        @JsonProperty("cleaned_length")
        private int cleanedLength;

        public ResultItem() {}

        public String getJobId() { return jobId; }
        public void setJobId(String jobId) { this.jobId = jobId; }

        public String getJdCleanText() { return jdCleanText; }
        public void setJdCleanText(String jdCleanText) { this.jdCleanText = jdCleanText; }

        public String getJdCleanHash() { return jdCleanHash; }
        public void setJdCleanHash(String jdCleanHash) { this.jdCleanHash = jdCleanHash; }

        public boolean isDeleteRow() { return deleteRow; }
        public void setDeleteRow(boolean deleteRow) { this.deleteRow = deleteRow; }

        public int getCleanedLength() { return cleanedLength; }
        public void setCleanedLength(int cleanedLength) { this.cleanedLength = cleanedLength; }
    }
}
