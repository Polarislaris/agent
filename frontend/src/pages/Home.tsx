import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getAllInterns, type InternPost } from "../api/internApi";
import { getProfile, type UserProfile } from "../api/userApi";
import { logout as logoutApi } from "../api/authApi";
import "./Home.css";

export default function Home() {
  const nav = useNavigate();
  const [posts, setPosts] = useState<InternPost[]>([]);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const isLoggedIn = localStorage.getItem("isLoggedIn");
    if (!isLoggedIn) {
      nav("/", { replace: true });
      return;
    }

    Promise.all([getAllInterns(), getProfile()])
      .then(([internData, profileData]) => {
        setPosts(internData);
        setUser(profileData);
      })
      .catch((err) => {
        console.error("Failed to load data", err);
      })
      .finally(() => setLoading(false));
  }, [nav]);

  const handleLogout = async () => {
    try {
      await logoutApi();
    } catch {
      // ignore logout errors
    }
    localStorage.removeItem("isLoggedIn");
    localStorage.removeItem("authToken");
    nav("/", { replace: true });
  };

  if (loading || !user) {
    return <div className="home-loading">Loading...</div>;
  }

  return (
    <div className="home-page">
      {/* ========== Sidebar ========== */}
      <aside className="home-sidebar">
        <div className="sidebar-avatar">{user.name.charAt(0)}</div>
        <div className="sidebar-name">{user.name}</div>

        <div className="sidebar-section">
          <h3>Skills</h3>
          <div className="sidebar-tags">
            {user.skills.map((s) => (
              <span key={s} className="sidebar-tag">{s}</span>
            ))}
          </div>
        </div>

        <div className="sidebar-section">
          <h3>Preferred Locations</h3>
          <div className="sidebar-tags">
            {user.preferredLocations.map((loc) => (
              <span key={loc} className="sidebar-tag">{loc}</span>
            ))}
          </div>
        </div>

        <div className="sidebar-section">
          <h3>Fields</h3>
          <div className="sidebar-tags">
            {user.fields.map((f) => (
              <span key={f} className="sidebar-tag">{f}</span>
            ))}
          </div>
        </div>

        <button className="sidebar-btn" onClick={() => nav("/profile")}>
          Edit Profile →
        </button>

        <button className="sidebar-btn" onClick={handleLogout} style={{ borderColor: "rgba(255,255,255,0.7)" }}>
          Logout
        </button>
      </aside>

      {/* ========== Main Content ========== */}
      <main className="home-main">
        <h1 className="home-title">Daily Intern Updates</h1>

        <div className="job-list">
          {posts.map((p) => (
            <div key={p.id} className="job-card" onClick={() => nav(`/intern/${p.id}`)}>
              <div className="job-id">{p.id}</div>
              <div className="job-info">
                <div className="job-title">{p.title}</div>
                <div className="job-meta">
                  <span>{p.company}</span>
                  <span>{p.base}</span>
                  <span>{p.date}</span>
                </div>
                <div className="job-extra">
                  <span className="job-stars">★★★★★</span>
                  <a className="job-apply-link" href="#" target="_blank" rel="noreferrer">Apply Link</a>
                </div>
              </div>
              <Link className="job-link" to={`/intern/${p.id}`} onClick={e => e.stopPropagation()}>
                View →
              </Link>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
