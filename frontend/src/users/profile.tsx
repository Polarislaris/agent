import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getProfile, updateProfile } from "../api/userApi";
import "./profile.css";

const MAX_LEN = { skills: 30, location: 40, fields: 30 };

function BubbleSection({
  title,
  items,
  onRemove,
  onAdd,
  placeholder,
  maxLen,
}: {
  title: string;
  items: string[];
  onRemove: (i: number) => void;
  onAdd: (v: string) => void;
  placeholder: string;
  maxLen: number;
}) {
  const [val, setVal] = useState("");

  const handleAdd = () => {
    const trimmed = val.trim();
    if (!trimmed) return;
    if (items.some((i) => i.toLowerCase() === trimmed.toLowerCase())) {
      setVal("");
      return;
    }
    onAdd(trimmed);
    setVal("");
  };

  return (
    <div className="profile-section">
      <h3 className="section-label">{title}</h3>
      <div className="bubble-wrap">
        {items.map((item, idx) => (
          <span key={item + idx} className="bubble">
            {item}
            <button
              className="bubble-x"
              onClick={() => onRemove(idx)}
              aria-label={`Remove ${item}`}
            >
              ×
            </button>
          </span>
        ))}
      </div>
      <div className="add-row">
        <input
          className="add-input"
          value={val}
          maxLength={maxLen}
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          placeholder={placeholder}
        />
        <button className="add-btn" onClick={handleAdd} disabled={!val.trim()}>
          + Add
        </button>
      </div>
      <span className="char-hint">{val.length}/{maxLen}</span>
    </div>
  );
}

export default function ProfileSetup() {
  const nav = useNavigate();
  const [name, setName] = useState("");
  const [skills, setSkills] = useState<string[]>([]);
  const [locations, setLocations] = useState<string[]>([]);
  const [fields, setFields] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saveMsg, setSaveMsg] = useState("");

  useEffect(() => {
    const isLoggedIn = localStorage.getItem("isLoggedIn");
    if (!isLoggedIn) {
      nav("/", { replace: true });
      return;
    }

    getProfile()
      .then((data) => {
        setName(data.name);
        setSkills(data.skills);
        setLocations(data.preferredLocations);
        setFields(data.fields);
      })
      .catch((err) => console.error("Failed to load profile", err))
      .finally(() => setLoading(false));
  }, [nav]);

  const handleSave = async () => {
    try {
      await updateProfile({ name, skills, preferredLocations: locations, fields });
      setSaveMsg("Changes saved!");
      setTimeout(() => setSaveMsg(""), 2000);
    } catch (err) {
      setSaveMsg("Save failed!");
      setTimeout(() => setSaveMsg(""), 2000);
      console.error("Failed to save profile", err);
    }
  };

  if (loading) {
    return <div className="profile-loading">Loading...</div>;
  }

  return (
    <div className="profile-page">
      {/* ---- Header ---- */}
      <div className="profile-header">
        <div className="profile-name">{name}</div>
        <div className="profile-subtitle">Manage your profile preferences</div>
      </div>

      {/* ---- Main Card ---- */}
      <div className="profile-card">
        <BubbleSection
          title="Skills"
          items={skills}
          onRemove={(i) => setSkills((p) => p.filter((_, idx) => idx !== i))}
          onAdd={(v) => setSkills((p) => [...p, v])}
          placeholder="e.g. React, Java, SQL..."
          maxLen={MAX_LEN.skills}
        />

        <BubbleSection
          title="Preferred Locations"
          items={locations}
          onRemove={(i) => setLocations((p) => p.filter((_, idx) => idx !== i))}
          onAdd={(v) => setLocations((p) => [...p, v])}
          placeholder="e.g. San Francisco, Remote..."
          maxLen={MAX_LEN.location}
        />

        <BubbleSection
          title="Fields"
          items={fields}
          onRemove={(i) => setFields((p) => p.filter((_, idx) => idx !== i))}
          onAdd={(v) => setFields((p) => [...p, v])}
          placeholder="e.g. Full-Stack, Backend..."
          maxLen={MAX_LEN.fields}
        />
      </div>

      {/* ---- Actions ---- */}
      <div className="profile-actions">
        <Link className="back-btn" to="/home">← Back to Home</Link>
        <button className="save-btn" onClick={handleSave}>Save Changes</button>
      </div>
      {saveMsg && (
        <div style={{position: "fixed", bottom: 32, left: 0, right: 0, textAlign: "center", zIndex: 9999}}>
          <span style={{background: "#667eea", color: "#fff", padding: "10px 24px", borderRadius: "8px", fontSize: "16px", boxShadow: "0 2px 8px rgba(102,126,234,0.18)"}}>{saveMsg}</span>
        </div>
      )}
    </div>
  );
}
