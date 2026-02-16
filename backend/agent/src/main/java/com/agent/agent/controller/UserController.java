package com.agent.agent.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.agent.agent.model.UserProfile;
import com.agent.agent.service.UserService;

@RestController
@RequestMapping("/api/user")
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    @GetMapping("/profile")
    public UserProfile getProfile() {
        return userService.getProfile();
    }

    @PutMapping("/profile")
    public UserProfile updateProfile(@RequestBody UserProfile profile) {
        return userService.updateProfile(profile);
    }
}
