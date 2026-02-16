package com.agent.agent.model;

import java.util.List;

public class UserProfile {
    private String name;
    private List<String> skills;
    private List<String> preferredLocations;
    private List<String> fields;

    public UserProfile() {}

    public UserProfile(String name, List<String> skills, List<String> preferredLocations, List<String> fields) {
        this.name = name;
        this.skills = skills;
        this.preferredLocations = preferredLocations;
        this.fields = fields;
    }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public List<String> getSkills() { return skills; }
    public void setSkills(List<String> skills) { this.skills = skills; }

    public List<String> getPreferredLocations() { return preferredLocations; }
    public void setPreferredLocations(List<String> preferredLocations) { this.preferredLocations = preferredLocations; }

    public List<String> getFields() { return fields; }
    public void setFields(List<String> fields) { this.fields = fields; }
}
