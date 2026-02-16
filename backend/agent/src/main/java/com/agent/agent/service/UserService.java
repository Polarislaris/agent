package com.agent.agent.service;

import java.util.ArrayList;
import java.util.Arrays;

import org.springframework.stereotype.Service;

import com.agent.agent.model.UserProfile;

@Service
public class UserService {

    // Placeholder: in-memory user profile (replace with DB later)
    private UserProfile currentUser;

    public UserService() {
        // Initialize with default placeholder data matching frontend
        currentUser = new UserProfile(
                "Yoyo",
                new ArrayList<>(Arrays.asList("React", "TypeScript", "Java", "Python", "SQL")),
                new ArrayList<>(Arrays.asList("San Francisco, CA", "Remote")),
                new ArrayList<>(Arrays.asList("Full-Stack", "Backend", "ML Engineering"))
        );
    }

    public UserProfile getProfile() {
        return currentUser;
    }

    public UserProfile updateProfile(UserProfile updated) {
        if (updated.getName() != null) {
            currentUser.setName(updated.getName());
        }
        if (updated.getSkills() != null) {
            currentUser.setSkills(updated.getSkills());
        }
        if (updated.getPreferredLocations() != null) {
            currentUser.setPreferredLocations(updated.getPreferredLocations());
        }
        if (updated.getFields() != null) {
            currentUser.setFields(updated.getFields());
        }
        return currentUser;
    }
}
