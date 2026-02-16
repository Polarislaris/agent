import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../api/authApi";
import logoImage from "../../img/logo.webp";
import "./login.css";

export default function Login() {
  const nav = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    try {
      const res = await login({ username, password });
      if (res.success) {
        setError(null);
        localStorage.setItem("isLoggedIn", "true");
        if (res.token) localStorage.setItem("authToken", res.token);
        nav("/home");
      } else {
        setError(res.message || "Invalid username or password.");
        setUsername("");
        setPassword("");
      }
    } catch {
      setError("Server error. Please try again later.");
      setUsername("");
      setPassword("");
    }
  };

  return (
    <div className="login-page">
      <div className="login-shell">
        <main className="login-main">
          <img src={logoImage} alt="SDE intern 2026 Logo" className="login-logo" />
          <h1 className="login-headline">SDE intern 2026</h1>
          <p className="login-subtitle">Welcome back! Please login to your account</p>

          <form onSubmit={onSubmit} className="login-form">
            <div className="login-field">
              <label className="login-label">Username</label>
              <input
                type="text"
                className="login-input"
                value={username}
                onChange={(e) => { setUsername(e.target.value); if (error) setError(null); }}
                placeholder="Enter your username"
                required
              />
            </div>

            <div className="login-field login-field--last">
              <label className="login-label">Password</label>
              <input
                type="password"
                className="login-input"
                value={password}
                onChange={(e) => { setPassword(e.target.value); if (error) setError(null); }}
                placeholder="Enter your password"
                required
              />
            </div>

            <button type="submit" className="login-submit">Login</button>

            {error && (
              <div className="login-error" role="alert" aria-live="assertive">
                {error}
              </div>
            )}
          </form>
        </main>
      </div>
    </div>
  );
}
