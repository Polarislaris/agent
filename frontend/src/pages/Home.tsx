import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getAllInterns, type InternPost } from "../api/internApi";
import { getProfile, type UserProfile } from "../api/userApi";
import { logout as logoutApi } from "../api/authApi";
import "./Home.css";

const PAGE_SIZE = 10;

export default function Home() {
  const nav = useNavigate();
  const [posts, setPosts] = useState<InternPost[]>([]);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  const totalPages = Math.ceil(posts.length / PAGE_SIZE);
  const pagedPosts = posts.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

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

  const goToPage = (p: number) => {
    setPage(p);
    // scroll main area back to top
    document.querySelector(".home-main")?.scrollTo({ top: 0, behavior: "smooth" });
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
        <div className="home-header">
          <h1 className="home-title">Daily Intern Updates</h1>
          <span className="home-count">{posts.length} positions</span>
        </div>

        <div className="job-list">
          {pagedPosts.map((p, idx) => (
            <div key={`${p.id}-${idx}`} className="job-card" onClick={() => nav(`/intern/${p.id}`)}>
              <div className="job-id">{(page - 1) * PAGE_SIZE + idx + 1}</div>
              <div className="job-info">
                <div className="job-title">{p.title}</div>
                <div className="job-meta">
                  <span>{p.company}</span>
                  <span>{p.base}</span>
                  <span>{p.date}</span>
                </div>
                <div className="job-extra">
                  {p.fitScore && <span className="job-stars">{p.fitScore.match(/★[★☆]*/)?.[0] || "★★★★★"}</span>}
                  {!p.fitScore && <span className="job-stars" style={{opacity: 0.4}}>Pending AI…</span>}
                  {p.avgSalary && <span className="job-salary">{p.avgSalary}</span>}
                  {p.applyLink && p.applyLink !== "#" && (
                    <a
                      className="job-apply-link"
                      href={p.applyLink}
                      target="_blank"
                      rel="noreferrer"
                      onClick={e => e.stopPropagation()}
                    >
                      Apply →
                    </a>
                  )}
                </div>
              </div>
              <Link className="job-link" to={`/intern/${p.id}`} onClick={e => e.stopPropagation()}>
                View →
              </Link>
            </div>
          ))}
        </div>

        {/* ========== Pagination ========== */}
        {totalPages > 1 && (
          <div className="pagination">
            <button
              className="page-btn"
              disabled={page === 1}
              onClick={() => goToPage(page - 1)}
            >
              ← Prev
            </button>

            {Array.from({ length: totalPages }, (_, i) => i + 1)
              .filter(p => p === 1 || p === totalPages || Math.abs(p - page) <= 2)
              .reduce<(number | string)[]>((acc, p, idx, arr) => {
                if (idx > 0 && p - (arr[idx - 1] as number) > 1) acc.push("...");
                acc.push(p);
                return acc;
              }, [])
              .map((item, idx) =>
                typeof item === "string" ? (
                  <span key={`dots-${idx}`} className="page-dots">…</span>
                ) : (
                  <button
                    key={item}
                    className={`page-btn ${page === item ? "page-active" : ""}`}
                    onClick={() => goToPage(item)}
                  >
                    {item}
                  </button>
                )
              )}

            <button
              className="page-btn"
              disabled={page === totalPages}
              onClick={() => goToPage(page + 1)}
            >
              Next →
            </button>

            <span className="page-info">
              Page {page} of {totalPages}
            </span>
          </div>
        )}
      </main>
    </div>
  );
}
