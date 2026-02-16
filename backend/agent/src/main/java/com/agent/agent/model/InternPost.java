package com.agent.agent.model;

import java.util.List;

public class InternPost {
    private String id;
    private String title;
    private String company;
    private String base;
    private String date;
    private String description;
    private List<String> requirements;
    private String applyLink;
    private CompanyInfo companyInfo;
    private String fitScore;
    private String difficulty;
    private String avgSalary;

    public InternPost() {}

    public InternPost(String id, String title, String company, String base, String date,
                      String description, List<String> requirements, String applyLink,
                      CompanyInfo companyInfo, String fitScore, String difficulty, String avgSalary) {
        this.id = id;
        this.title = title;
        this.company = company;
        this.base = base;
        this.date = date;
        this.description = description;
        this.requirements = requirements;
        this.applyLink = applyLink;
        this.companyInfo = companyInfo;
        this.fitScore = fitScore;
        this.difficulty = difficulty;
        this.avgSalary = avgSalary;
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }

    public String getCompany() { return company; }
    public void setCompany(String company) { this.company = company; }

    public String getBase() { return base; }
    public void setBase(String base) { this.base = base; }

    public String getDate() { return date; }
    public void setDate(String date) { this.date = date; }

    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }

    public List<String> getRequirements() { return requirements; }
    public void setRequirements(List<String> requirements) { this.requirements = requirements; }

    public String getApplyLink() { return applyLink; }
    public void setApplyLink(String applyLink) { this.applyLink = applyLink; }

    public CompanyInfo getCompanyInfo() { return companyInfo; }
    public void setCompanyInfo(CompanyInfo companyInfo) { this.companyInfo = companyInfo; }

    public String getFitScore() { return fitScore; }
    public void setFitScore(String fitScore) { this.fitScore = fitScore; }

    public String getDifficulty() { return difficulty; }
    public void setDifficulty(String difficulty) { this.difficulty = difficulty; }

    public String getAvgSalary() { return avgSalary; }
    public void setAvgSalary(String avgSalary) { this.avgSalary = avgSalary; }
}
