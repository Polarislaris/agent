package com.agent.agent.model;

public class CompanyInfo {
    private String size;
    private String founded;
    private String business;

    public CompanyInfo() {}

    public CompanyInfo(String size, String founded, String business) {
        this.size = size;
        this.founded = founded;
        this.business = business;
    }

    public String getSize() { return size; }
    public void setSize(String size) { this.size = size; }

    public String getFounded() { return founded; }
    public void setFounded(String founded) { this.founded = founded; }

    public String getBusiness() { return business; }
    public void setBusiness(String business) { this.business = business; }
}
