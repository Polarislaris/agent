import { useParams, Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { getInternById, type InternPost } from "../api/internApi";
import "./InternDetail.css";

const FIT_ANALYSIS_PLACEHOLDER = `Your profile aligns strongly with this role because the core stack overlaps with projects you have already shipped, while the remaining gaps are learnable within the internship timeframe. You demonstrate comfort with front to back workflows, translating product requirements into clean components, wiring APIs, and validating results with tests. The team values ownership and communication, and your experience collaborating in small groups suggests you will ramp quickly. To maximize fit, focus on polishing one flagship project with measurable outcomes, and be ready to explain tradeoffs, performance decisions, and how you handled feedback. A short portfolio walkthrough, a concise resume narrative, and a clear curiosity for the domain will position you as a top candidate. Overall, this is a strong match with high upside if you prepare concrete examples. Consider brushing up on system design basics, documenting your debugging process, and sharing one story about overcoming a tricky production issue recently.`;

const APPLY_DIFFICULTY_PLACEHOLDER = `Competition is moderate to high, but the screening process favors candidates who demonstrate clarity, not just raw skill. Expect an initial resume pass, a short online assessment, and one to two technical interviews focused on practical problem solving. If the company is smaller, interviews may emphasize real-world debugging and building features under time constraints. To reduce difficulty, tailor your resume to the job description, highlight relevant coursework or internships, and prepare a tight elevator pitch. Practice explaining your approach out loud and be ready to discuss tradeoffs, testing, and edge cases. Applicants who show curiosity about the product and ask thoughtful questions often stand out. With focused preparation and a few mock interviews, the barrier feels manageable. Scheduling may move quickly, so keep availability flexible, review core algorithms, and bring one concise story showing impact, ownership, and persistence. That preparation typically shortens the process and builds interviewer confidence in you.`;

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
              <span className="d-card-row-value">{job.companyInfo.size}</span>
            </div>
            <div className="d-card-row">
              <span className="d-card-row-label">Founded</span>
              <span className="d-card-row-value">{job.companyInfo.founded}</span>
            </div>
            <div className="d-card-row">
              <span className="d-card-row-label">Business</span>
              <span className="d-card-row-value">{job.companyInfo.business}</span>
            </div>
          </div>

          <div className="d-card">
            <div className="d-card-header">
              <div className="d-section-title">Fit Analysis</div>
              <div className="d-stars" aria-label="5 out of 5 stars">★★★★★</div>
            </div>
            <div className="d-fit-text">{FIT_ANALYSIS_PLACEHOLDER}</div>
          </div>

          <div className="d-card">
            <div className="d-card-header">
              <div className="d-section-title">Apply Difficulty</div>
              <div className="d-stars" aria-label="5 out of 5 stars">★★★★★</div>
            </div>
            <div className="d-fit-text">{APPLY_DIFFICULTY_PLACEHOLDER}</div>
          </div>

          <div className="d-card">
            <div className="d-section-title">Average Salary</div>
            <div className="d-salary-big">{job.avgSalary}</div>
            <div className="d-salary-note">Estimated hourly rate for this role</div>
          </div>
        </div>
      </div>
    </div>
  );
}
