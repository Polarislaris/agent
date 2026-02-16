package com.agent.agent.service;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

import org.springframework.stereotype.Service;

import com.agent.agent.model.LoginRequest;
import com.agent.agent.model.LoginResponse;

@Service
public class AuthService {

    // Placeholder: in-memory user store (replace with DB later)
    private static final Map<String, String> USERS = Map.of(
            "123", "123",
            "admin", "admin"
    );

    // Placeholder: in-memory token store (replace with JWT / Redis later)
    private final ConcurrentHashMap<String, String> activeTokens = new ConcurrentHashMap<>();

    public LoginResponse login(LoginRequest request) {
        String storedPassword = USERS.get(request.getUsername());
        if (storedPassword != null && storedPassword.equals(request.getPassword())) {
            String token = UUID.randomUUID().toString();
            activeTokens.put(token, request.getUsername());
            return new LoginResponse(true, "Login successful", token);
        }
        return new LoginResponse(false, "Invalid username or password", null);
    }

    public boolean validateToken(String token) {
        return token != null && activeTokens.containsKey(token);
    }

    public void logout(String token) {
        if (token != null) {
            activeTokens.remove(token);
        }
    }
}
