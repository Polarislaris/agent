import { useParams, Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { getInternById, type InternPost } from "../api/internApi";
import "./InternDetail.css";

const FIT_ANALYSIS_PLACEHOLDER = `AI analysis is being generated. The fit analysis will appear here once the background AI enrichment completes. Refresh the page in a moment to see personalized insights about how well this role matches your profile.`;

const APPLY_DIFFICULTY_PLACEHOLDER = `AI analysis is being generated. The difficulty assessment will appear here once background processing completes. Refresh the page shortly to see detailed analysis of competition level and interview preparation tips.`;

export default function InternDetail() {
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const [job, setJob] = useState<InternPost | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    const isLoggedIn = localStorage.getItem("isLoggedIn");
    if (!isLoggedIn) {
      nav("/", { replace: true });
      return;
    }

    if (!id) {
      setNotFound(true);
      setLoading(false);
      return;
    }

    getInternById(id)
      .then((data) => setJob(data))
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false));
  }, [id, nav]);

  if (loading) {
    return <div className="detail-loading">Loading...</div>;
  }

  if (notFound || !job) {
    return (
      <div className="detail-not-found">
        <h2>Job Not Found</h2>
        <Link className="detail-not-found-link" to="/home">← Back to Home</Link>
      </div>
    );
  }

  return (
    <div className="detail-page">
      {/* ========== Top Header ========== */}
      <header className="detail-topbar">
        <div className="detail-topbar-id">{job.id}</div>
        <div>
          <h1>{job.title}</h1>
          <div className="detail-topbar-sub">{job.company} · {job.base} · {job.date}</div>
        </div>
      </header>

      {/* ========== Dual Panels ========== */}
      <div className="detail-body">
        {/* ---- Left Panel: Job Info ---- */}
        <div className="detail-left">
          <div>
            <div className="d-section-title">Overview</div>
            <div className="d-row">
              <span className="d-label">Published</span>
              <span className="d-value">{job.date}</span>
            </div>
            <div className="d-row" style={{ marginTop: 6 }}>
              <span className="d-label">Location</span>
              <span className="d-value">{job.base}</span>
            </div>
          </div>

          <div>
            <div className="d-section-title">Description</div>
            <div className="d-desc-box">{job.description}</div>
          </div>

          <div>
            <div className="d-section-title">Requirements</div>
            <div className="d-tags">
              {job.requirements.map((r) => (
                <span key={r} className="d-tag">{r}</span>
              ))}
            </div>
          </div>

          <div className="d-actions">
            <a className="d-apply" href={job.applyLink} target="_blank" rel="noreferrer">Apply Now</a>
            <Link className="d-back" to="/home">← Back</Link>
          </div>
        </div>

        {/* ---- Right Panel: Analysis ---- */}
        <div className="detail-right">
          <div className="d-card">
            <div className="d-section-title">Company Info</div>
            <div className="d-card-row">
              <span className="d-card-row-label">Company</span>
              <span className="d-card-row-value">{job.company}</span>
            </div>
            <div className="d-card-row">
              <span className="d-card-row-label">Size</span>
              <span className="d-card-row-value">{job.companyInfo.size || "Pending..."}</span>
            </div>
            <div className="d-card-row">
              <span className="d-card-row-label">Founded</span>
              <span className="d-card-row-value">{job.companyInfo.founded || "Pending..."}</span>
            </div>
            <div className="d-card-row">
              <span className="d-card-row-label">Business</span>
              <span className="d-card-row-value">{job.companyInfo.business || "Pending..."}</span>
            </div>
          </div>

          <div className="d-card">
            <div className="d-card-header">
              <div className="d-section-title">Fit Analysis</div>
              <div className="d-stars" aria-label="fit score">
                {job.fitScore ? job.fitScore.match(/★[★☆]*/)?.[0] || "★★★★★" : "★★★★★"}
              </div>
            </div>
            <div className="d-fit-text">
              {job.fitScore
                ? job.fitScore.replace(/^★[★☆]*\s*/, "")
                : FIT_ANALYSIS_PLACEHOLDER}
            </div>
          </div>

          <div className="d-card">
            <div className="d-card-header">
              <div className="d-section-title">Apply Difficulty</div>
              <div className="d-stars" aria-label="difficulty">
                {job.difficulty ? job.difficulty.split(" ")[0] || "—" : "—"}
              </div>
            </div>
            <div className="d-fit-text">
              {job.difficulty || APPLY_DIFFICULTY_PLACEHOLDER}
            </div>
          </div>

          <div className="d-card">
            <div className="d-section-title">Average Salary</div>
            <div className="d-salary-big">{job.avgSalary || "Pending AI analysis..."}</div>
            <div className="d-salary-note">Estimated hourly rate for this role</div>
          </div>
        </div>
      </div>
    </div>
  );
}
