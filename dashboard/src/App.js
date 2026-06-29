import { useState, useEffect, useRef } from "react";
import axios from "axios";

const API = process.env.REACT_APP_API_URL || "http://localhost:8000";

const PRESET_QUESTIONS = [
  "How many visitors came today?",
  "How many people were in the venue between 8pm and 9pm?",
  "What was the average wait time this hour?",
  "How many people left without being served today?",
  "Which hour had the most visitors?",
  "What was the busiest time period today?",
  "Who stayed the longest and for how long?",
  "How does the abandonment rate look today?",
  "How many visitors came in the last 30 minutes?",
  "What percentage of visitors were served today?",
];

function KPICard({ icon, label, value, detail, color = "#f59e0b" }) {
  return (
    <div style={{
      background: "#111827", border: "1px solid #1f2937",
      borderRadius: 16, padding: "24px 28px", flex: 1, minWidth: 180,
      borderTop: `3px solid ${color}`
    }}>
      <div style={{ fontSize: 22, marginBottom: 8 }}>{icon}</div>
      <div style={{ color: "#6b7280", fontSize: 12, fontWeight: 600,
        textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>{label}</div>
      <div style={{ color: "#f9fafb", fontSize: 32, fontWeight: 800,
        lineHeight: 1, marginBottom: 6 }}>{value}</div>
      {detail && <div style={{ color: "#4b5563", fontSize: 12 }}>{detail}</div>}
    </div>
  );
}

function dwellLabel(s) {
  if (!s) return "—";
  if (s < 60) return `${parseFloat(s).toFixed(0)}s`;
  return `${(s / 60).toFixed(1)} min`;
}

function formatTime(iso) {
  if (!iso) return "—";
  return iso.slice(11, 19) + " UTC";
}

function UploadScreen({ onProcessingStart }) {
  const [dragOver, setDragOver] = useState(false);
  const [urlInput, setUrlInput] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef();

  const handleFile = async (file) => {
    if (!file) return;
    setUploading(true);
    setError("");
    const form = new FormData();
    form.append("file", file);
    try {
      const r = await axios.post(`${API}/upload`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      onProcessingStart(r.data.job_id);
    } catch (e) {
      setError("Upload failed. Make sure the API is running.");
      setUploading(false);
    }
  };

  const handleUrl = async () => {
    if (!urlInput.trim()) return;
    setUploading(true);
    setError("");
    try {
      const r = await axios.post(`${API}/upload/url`, { url: urlInput });
      if (r.data.error) { setError(r.data.error); setUploading(false); return; }
      onProcessingStart(r.data.job_id);
    } catch (e) {
      setError("Failed to process URL.");
      setUploading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh", background: "#0a0f1a",
      display: "flex", flexDirection: "column", alignItems: "center",
      justifyContent: "center", padding: 40, fontFamily: "'Inter', sans-serif",
    }}>
      <div style={{ color: "#f59e0b", fontSize: 11, fontWeight: 700,
        letterSpacing: 3, textTransform: "uppercase", marginBottom: 12 }}>
        Powered by Computer Vision + AI
      </div>
      <h1 style={{ color: "#f9fafb", fontSize: 36, fontWeight: 800,
        margin: "0 0 8px", textAlign: "center" }}>
        Customer Intelligence Platform
      </h1>
      <p style={{ color: "#4b5563", fontSize: 15, marginBottom: 48,
        textAlign: "center", maxWidth: 500 }}>
        Upload your venue footage and get instant insights on visitor behaviour,
        dwell time, and service efficiency.
      </p>

      <div style={{ width: "100%", maxWidth: 560 }}>
        {/* Drag & Drop */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files[0]); }}
          onClick={() => fileRef.current.click()}
          style={{
            border: `2px dashed ${dragOver ? "#f59e0b" : "#374151"}`,
            borderRadius: 16, padding: "48px 32px", textAlign: "center",
            cursor: "pointer", marginBottom: 24,
            background: dragOver ? "#1a1500" : "#111827", transition: "all 0.2s",
          }}
        >
          <div style={{ fontSize: 40, marginBottom: 12 }}>🎥</div>
          <div style={{ color: "#f9fafb", fontWeight: 600, fontSize: 16, marginBottom: 6 }}>
            Drop your video here
          </div>
          <div style={{ color: "#4b5563", fontSize: 13 }}>
            MP4, MOV, AVI supported · or click to browse
          </div>
          <input ref={fileRef} type="file" accept="video/*"
            style={{ display: "none" }} onChange={(e) => handleFile(e.target.files[0])} />
        </div>

        {/* Divider */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
          <div style={{ flex: 1, height: 1, background: "#1f2937" }} />
          <span style={{ color: "#4b5563", fontSize: 12, fontWeight: 600,
            textTransform: "uppercase", letterSpacing: 1 }}>or paste a YouTube URL</span>
          <div style={{ flex: 1, height: 1, background: "#1f2937" }} />
        </div>

        {/* URL input */}
        <div style={{ display: "flex", gap: 12, marginBottom: 24 }}>
          <input
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleUrl()}
            placeholder="https://www.youtube.com/watch?v=..."
            style={{
              flex: 1, background: "#111827", border: "1px solid #374151",
              borderRadius: 10, padding: "12px 18px", color: "#f9fafb",
              fontSize: 14, outline: "none"
            }}
          />
          <button onClick={handleUrl} disabled={uploading} style={{
            background: "#f59e0b", color: "#0a0f1a", border: "none",
            borderRadius: 10, padding: "12px 24px", fontWeight: 800,
            fontSize: 14, cursor: "pointer"
          }}>
            Analyse URL
          </button>
        </div>

        {error && (
          <div style={{ background: "#1c0a00", border: "1px solid #7c2d12",
            borderRadius: 10, padding: "12px 16px", color: "#f97316",
            fontSize: 13, marginBottom: 16 }}>{error}</div>
        )}
        {uploading && (
          <div style={{ textAlign: "center", color: "#6b7280", fontSize: 13 }}>
            Uploading video...
          </div>
        )}

        {/* Feature list */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr",
          gap: 12, marginTop: 40 }}>
          {[
            ["👥", "Person Detection", "Identifies every unique visitor"],
            ["🔄", "Cross-frame Tracking", "Follows people across camera angles"],
            ["⏱", "Dwell Time Analysis", "Measures how long each visitor stays"],
            ["🤖", "AI Business Insights", "Ask questions in plain English"],
          ].map(([icon, title, desc]) => (
            <div key={title} style={{ background: "#111827",
              border: "1px solid #1f2937", borderRadius: 12, padding: 16 }}>
              <div style={{ fontSize: 20, marginBottom: 8 }}>{icon}</div>
              <div style={{ color: "#f9fafb", fontWeight: 600,
                fontSize: 13, marginBottom: 4 }}>{title}</div>
              <div style={{ color: "#4b5563", fontSize: 12 }}>{desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ProcessingScreen({ jobId, onComplete }) {
  const [job, setJob] = useState({ status: "queued", progress: 0, stage: "Queued" });

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const r = await axios.get(`${API}/job/${jobId}`);
        setJob(r.data);
        if (r.data.status === "done" || r.data.status === "error") {
          clearInterval(interval);
          if (r.data.status === "done") setTimeout(onComplete, 800);
        }
      } catch (e) {}
    }, 1500);
    return () => clearInterval(interval);
  }, [jobId, onComplete]);

  const stages = [
    "Analysing video characteristics...",
    "Detecting people...",
    "Building identity profiles...",
    "Analysing behaviour...",
    "Evaluating data quality...",
    "Generating insights...",
    "Complete",
  ];

  return (
    <div style={{ minHeight: "100vh", background: "#0a0f1a",
      display: "flex", flexDirection: "column", alignItems: "center",
      justifyContent: "center", padding: 40, fontFamily: "'Inter', sans-serif" }}>
      <div style={{ width: "100%", maxWidth: 480, textAlign: "center" }}>
        <div style={{ fontSize: 48, marginBottom: 24 }}>
          {job.status === "error" ? "❌" : job.status === "done" ? "✅" : "⚙️"}
        </div>
        <h2 style={{ color: "#f9fafb", fontSize: 24, fontWeight: 800, marginBottom: 8 }}>
          {job.status === "error" ? "Processing Failed" :
           job.status === "done" ? "Analysis Complete!" : "Analysing Your Video"}
        </h2>
        <p style={{ color: "#6b7280", fontSize: 14, marginBottom: 40 }}>{job.stage}</p>

        {/* Progress bar */}
        <div style={{ background: "#1f2937", borderRadius: 8, height: 8,
          marginBottom: 32, overflow: "hidden" }}>
          <div style={{
            height: "100%", borderRadius: 8,
            background: job.status === "error" ? "#ef4444" : "#f59e0b",
            width: `${job.progress || 0}%`, transition: "width 0.5s ease"
          }} />
        </div>

        {/* Stage checklist */}
        <div style={{ textAlign: "left" }}>
          {stages.map((s, i) => {
            const stageProgress = (i / (stages.length - 1)) * 100;
            const done = (job.progress || 0) > stageProgress;
            const active = job.stage === s;
            return (
              <div key={s} style={{ display: "flex", alignItems: "center",
                gap: 12, padding: "8px 0", borderBottom: "1px solid #1f2937" }}>
                <div style={{
                  width: 20, height: 20, borderRadius: "50%",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 11, fontWeight: 700, flexShrink: 0,
                  background: done ? "#f59e0b" : active ? "#1f2937" : "#111827",
                  color: done ? "#0a0f1a" : active ? "#f59e0b" : "#374151",
                  border: active ? "2px solid #f59e0b" : "2px solid transparent",
                }}>
                  {done ? "✓" : i + 1}
                </div>
                <span style={{
                  color: done ? "#f9fafb" : active ? "#f59e0b" : "#374151",
                  fontSize: 13, fontWeight: active ? 600 : 400
                }}>{s}</span>
              </div>
            );
          })}
        </div>

        {job.status === "error" && (
          <div style={{ marginTop: 24, color: "#f97316", fontSize: 13 }}>
            {job.stage}
          </div>
        )}
      </div>
    </div>
  );
}

function DashboardScreen({ onReset }) {
  const [summary, setSummary] = useState(null);
  const [persons, setPersons] = useState([]);
  const [hourly, setHourly] = useState([]);
  const [biq, setBiq] = useState(null);
  const [baseline, setBaseline] = useState(null);
  const [venues, setVenues] = useState([]);
  const [selectedVenue, setSelectedVenue] = useState("default");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [ratings, setRatings] = useState({});
  const [hoveredCard, setHoveredCard] = useState(null);

  const fetchData = (venueId = selectedVenue) => {
    axios.get(`${API}/metrics/summary`).then(r => {
      setSummary(r.data);
      setLastUpdated(new Date().toLocaleTimeString());
    }).catch(() => {});
    axios.get(`${API}/metrics/persons`).then(r => setPersons(r.data)).catch(() => {});
    axios.get(`${API}/metrics/hourly`).then(r => setHourly(r.data)).catch(() => {});
    axios.get(`${API}/metrics/business_iq`).then(r => setBiq(r.data)).catch(() => {});
    axios.get(`${API}/metrics/baseline?venue_id=${venueId}`).then(r => setBaseline(r.data)).catch(() => {});
    axios.get(`${API}/venues`).then(r => {
      if (r.data && r.data.length > 0) {
        setVenues(r.data);
      } else {
        setVenues([{ venue_id: "default", memory_slots: 0, runs_recorded: 0 }]);
      }
    }).catch(() => {
      setVenues([{ venue_id: "default", memory_slots: 0, runs_recorded: 0 }]);
    });
  };

  useEffect(() => {
    fetchData(selectedVenue);
  }, [selectedVenue]); // eslint-disable-line

  const askQuestion = async (q) => {
    const query = q || question;
    if (!query.trim()) return;
    setQuestion(query);
    setLoading(true);
    setAnswer(null);
    try {
      const r = await axios.post(`${API}/ask?venue_id=${selectedVenue}`, { question: query });
      setAnswer(r.data);
    } catch (e) {
      setAnswer({ plain_answer: "Could not reach the analytics engine." });
    }
    setLoading(false);
  };

  const rateAnswer = async (answerId, rating) => {
    if (!answerId) return;
    setRatings(prev => ({ ...prev, [answerId]: rating }));
    try {
      await axios.post(`${API}/ask/${answerId}/rate`, { rating });
    } catch (e) {}
  };

  const chartData = persons.filter(p => p.dwell_seconds > 0);
  const maxDwell = Math.max(...chartData.map(d => d.dwell_seconds), 1);

  const glassStyle = {
    background: "rgba(17, 24, 39, 0.6)",
    backdropFilter: "blur(16px)",
    border: "1px solid rgba(255, 255, 255, 0.08)",
    borderRadius: 20,
    boxShadow: "0 10px 30px rgba(0, 0, 0, 0.5)",
    transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)"
  };

  return (
    <div style={{ minHeight: "100vh", background: "radial-gradient(circle at top left, #0e172a, #020617)",
      color: "#f9fafb", fontFamily: "'Inter', sans-serif",
      padding: "48px 40px", maxWidth: 1100, margin: "0 auto" }}>

      {/* Header Panel */}
      <div style={{ display: "flex", justifyContent: "space-between",
        alignItems: "center", marginBottom: 40, flexWrap: "wrap", gap: 20 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <span style={{
              background: "linear-gradient(135deg, #f59e0b, #ef4444)",
              color: "#020617", fontSize: 10, fontWeight: 800,
              padding: "4px 8px", borderRadius: 6, textTransform: "uppercase", letterSpacing: 1.5
            }}>Real-time Vision</span>
            {baseline?.has_memory && (
              <span style={{
                background: "rgba(16, 185, 129, 0.15)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                color: "#10b981", fontSize: 10, fontWeight: 700,
                padding: "3px 8px", borderRadius: 6, display: "flex", alignItems: "center", gap: 4
              }}>
                🧠 Learned: {baseline.runs_recorded} runs
              </span>
            )}
          </div>
          <h1 style={{ fontSize: 36, fontWeight: 900, margin: 0, letterSpacing: "-0.5px",
            background: "linear-gradient(to right, #f9fafb, #9ca3af)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            Customer Intelligence
          </h1>
          <p style={{ color: "#9ca3af", fontSize: 14, margin: "6px 0 0" }}>
            AI-driven space performance & service metrics
          </p>
        </div>

        {/* Venue Selector and Control Toolbar */}
        <div style={{ display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
          {venues.length > 0 && (
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ color: "#6b7280", fontSize: 12, fontWeight: 600 }}>VENUE:</span>
              <select
                value={selectedVenue}
                onChange={(e) => setSelectedVenue(e.target.value)}
                style={{
                  background: "rgba(31, 41, 55, 0.8)", border: "1px solid rgba(255, 255, 255, 0.15)",
                  color: "#f9fafb", borderRadius: 10, padding: "8px 16px", fontSize: 13,
                  fontWeight: 700, outline: "none", cursor: "pointer", transition: "all 0.2s",
                  boxShadow: "0 4px 12px rgba(0, 0, 0, 0.2)"
                }}
              >
                {venues.map(v => (
                  <option key={v.venue_id} value={v.venue_id}>
                    {v.venue_id.toUpperCase()} ({v.runs_recorded || 0} Runs)
                  </option>
                ))}
              </select>
            </div>
          )}
          <button onClick={() => fetchData(selectedVenue)} style={{
            background: "rgba(31, 41, 55, 0.5)", border: "1px solid rgba(255, 255, 255, 0.08)",
            color: "#f9fafb", borderRadius: 10, padding: "8px 16px",
            fontSize: 13, cursor: "pointer", transition: "all 0.2s", fontWeight: 600 }}>↻ Refresh</button>
          <button onClick={onReset} style={{
            background: "linear-gradient(135deg, #f59e0b, #d97706)", border: "none",
            color: "#020617", borderRadius: 10, padding: "8px 18px",
            fontSize: 13, fontWeight: 700, cursor: "pointer", transition: "all 0.2s",
            boxShadow: "0 4px 14px rgba(245, 158, 11, 0.3)" }}>+ New Video</button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      {summary && (
        <div style={{ display: "flex", gap: 20, marginBottom: 32, flexWrap: "wrap" }}>
          {[
            { id: "visitors", icon: "👥", label: "Total Visitors", val: summary.total_visitors, detail: "unique profiles", color: "#f59e0b" },
            { id: "dwell", icon: "⏱", label: "Avg Dwell Time", val: dwellLabel(summary.avg_dwell_seconds), detail: "per customer visit", color: "#3b82f6" },
            { id: "longest", icon: "📈", label: "Longest Stay", val: dwellLabel(summary.max_dwell_seconds), detail: "maximum peak session", color: "#8b5cf6" },
            { 
              id: "abandoned", 
              icon: "🚪", 
              label: "Left Unserved", 
              val: `${summary.abandonment_rate_pct}%`, 
              detail: `${summary.abandoned_count} of ${summary.total_visitors} unserved`, 
              color: summary.abandonment_rate_pct > 50 ? "#ef4444" : "#10b981" 
            }
          ].map((card) => {
            const isHovered = hoveredCard === card.id;
            return (
              <div
                key={card.id}
                onMouseEnter={() => setHoveredCard(card.id)}
                onMouseLeave={() => setHoveredCard(null)}
                style={{
                  ...glassStyle,
                  flex: 1,
                  minWidth: 220,
                  padding: "24px 28px",
                  borderTop: `4px solid ${card.color}`,
                  transform: isHovered ? "translateY(-4px)" : "none",
                  boxShadow: isHovered ? `0 15px 35px rgba(0, 0, 0, 0.6), 0 0 15px ${card.color}22` : "0 10px 30px rgba(0, 0, 0, 0.4)",
                  background: isHovered ? "rgba(31, 41, 55, 0.6)" : "rgba(17, 24, 39, 0.6)"
                }}
              >
                <div style={{ fontSize: 24, marginBottom: 12 }}>{card.icon}</div>
                <div style={{ color: "#9ca3af", fontSize: 11, fontWeight: 700,
                  textTransform: "uppercase", letterSpacing: 1.2, marginBottom: 8 }}>{card.label}</div>
                <div style={{ color: "#f9fafb", fontSize: 36, fontWeight: 900,
                  lineHeight: 1, marginBottom: 8 }}>{card.val}</div>
                <div style={{ color: "#4b5563", fontSize: 12, fontWeight: 500 }}>{card.detail}</div>
              </div>
            );
          })}
        </div>
      )}

      {/* Business IQ & Analytics Fusion Box */}
      {biq && (
        <div style={{ ...glassStyle, padding: "32px", marginBottom: 32,
          display: "flex", gap: 40, alignItems: "center", flexWrap: "wrap",
          background: "linear-gradient(145deg, rgba(17, 24, 39, 0.8), rgba(3, 7, 18, 0.8))" }}>
          <div style={{ textAlign: "center", flexShrink: 0 }}>
            <div style={{
              width: 140, height: 140, borderRadius: "50%",
              border: `6px solid ${biq.color}`,
              display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center",
              background: "#020617",
              boxShadow: `0 0 25px ${biq.color}25`
            }}>
              <div style={{ color: biq.color, fontSize: 44, fontWeight: 900, lineHeight: 1 }}>{biq.score}</div>
              <div style={{ color: "#9ca3af", fontSize: 14, fontWeight: 700, marginTop: 4 }}>GRADE {biq.grade}</div>
            </div>
            <div style={{ color: "#9ca3af", fontSize: 11, fontWeight: 700,
              textTransform: "uppercase", letterSpacing: 1.5, marginTop: 14 }}>OPERATIONAL SCORE</div>
          </div>
          
          <div style={{ flex: 1, minWidth: 280 }}>
            <div style={{ color: "#f9fafb", fontWeight: 800, fontSize: 18, marginBottom: 6 }}>
              Venue Operational IQ
            </div>
            <div style={{ color: "#9ca3af", fontSize: 13, marginBottom: 20 }}>
              Composite metric evaluating service speed, dwell parameters, and floor efficiency.
            </div>
            {[
              ["Service Rate", biq.breakdown.service_score, "#10b981"],
              ["Dwell Quality", biq.breakdown.dwell_score, "#3b82f6"],
              ["Attendance Score", biq.breakdown.abandonment_score, "#f59e0b"],
            ].map(([label, score, color]) => (
              <div key={label} style={{ marginBottom: 14 }}>
                <div style={{ display: "flex", justifyContent: "space-between",
                  fontSize: 13, marginBottom: 6, fontWeight: 600 }}>
                  <span style={{ color: "#9ca3af" }}>{label}</span>
                  <span style={{ color: "#f9fafb" }}>{score}/100</span>
                </div>
                <div style={{ background: "rgba(31, 41, 55, 0.6)", borderRadius: 10, height: 8, overflow: "hidden" }}>
                  <div style={{ width: `${score}%`, height: "100%",
                    background: `linear-gradient(90deg, ${color}cc, ${color})`, borderRadius: 10, transition: "width 0.8s ease" }} />
                </div>
              </div>
            ))}
          </div>

          <div style={{ flex: 1, minWidth: 280 }}>
            <div style={{ color: "#9ca3af", fontSize: 11, fontWeight: 700,
              textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 14 }}>
              Operational Recommendations
            </div>
            {biq.insights && biq.insights.map((ins, i) => (
              <div key={i} style={{ display: "flex", gap: 12, marginBottom: 12, fontSize: 13, alignItems: "flex-start" }}>
                <span style={{ color: biq.color, flexShrink: 0, fontWeight: "bold" }}>✦</span>
                <span style={{ color: "#9ca3af", lineHeight: 1.4 }}>{ins}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Baseline / Self-Learning Panel */}
      {baseline && baseline.has_memory && (
        <div style={{
          ...glassStyle,
          background: "linear-gradient(145deg, rgba(10, 22, 40, 0.7), rgba(3, 7, 18, 0.7))",
          border: "1px solid rgba(96, 165, 250, 0.2)",
          padding: "28px",
          marginBottom: 32
        }}>
          <div style={{ display: "flex", justifyContent: "space-between",
            alignItems: "center", marginBottom: 20 }}>
            <div>
              <div style={{ color: "#60a5fa", fontSize: 12, fontWeight: 800,
                textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 4 }}>
                🧠 VENUE SELF-LEARNING BASES
              </div>
              <div style={{ color: "#9ca3af", fontSize: 13 }}>
                Historical comparisons for current {baseline.current_slot.day_of_week} ({baseline.current_slot.hour}:00 slot)
              </div>
            </div>
          </div>

          {/* Anomaly Alerts Container */}
          {baseline.anomaly_flags && baseline.anomaly_flags.length > 0 && (
            <div style={{ marginBottom: 20 }}>
              {baseline.anomaly_flags.map((flag, i) => (
                <div key={i} style={{
                  background: "rgba(69, 26, 3, 0.7)", border: "1px solid #92400e",
                  borderRadius: 12, padding: "12px 18px", marginBottom: 10,
                  color: "#fbbf24", fontSize: 13, fontWeight: 600, display: "flex", alignItems: "center", gap: 8
                }}>
                  <span>⚠️</span>
                  <span>{flag}</span>
                </div>
              ))}
            </div>
          )}

          {/* Comparators */}
          {baseline.live_today && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16 }}>
              {[
                {
                  label: "Traffic (Visitors)",
                  live: baseline.live_today.visitors,
                  baseline: baseline.baselines.find(b => b.metric_type === "visitor_count")?.value,
                  format: v => Math.round(v),
                  color: "#60a5fa"
                },
                {
                  label: "Customer Dwell",
                  live: baseline.live_today.avg_dwell_seconds,
                  baseline: baseline.baselines.find(b => b.metric_type === "avg_dwell")?.value,
                  format: v => v ? dwellLabel(v) : "—",
                  color: "#a78bfa"
                },
                {
                  label: "Abandonment Rate",
                  live: baseline.live_today.abandonment_rate_pct,
                  baseline: baseline.baselines.find(b => b.metric_type === "abandonment_rate")?.value,
                  format: v => v != null ? `${v.toFixed(1)}%` : "—",
                  color: "#f87171"
                },
              ].map(({ label, live, baseline: base, format, color }) => (
                <div key={label} style={{
                  background: "rgba(17, 24, 39, 0.4)", borderRadius: 16,
                  padding: "20px", borderLeft: `4px solid ${color}`,
                  border: "1px solid rgba(255, 255, 255, 0.05)"
                }}>
                  <div style={{ color: "#9ca3af", fontSize: 12, fontWeight: 700,
                    textTransform: "uppercase", letterSpacing: 1.2, marginBottom: 14 }}>
                    {label}
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                      <div style={{ color: "#6b7280", fontSize: 10, fontWeight: 700, marginBottom: 4 }}>TODAY</div>
                      <div style={{ color: color, fontSize: 24, fontWeight: 900 }}>
                        {live != null ? format(live) : "—"}
                      </div>
                    </div>
                    <div style={{ color: "#374151", fontSize: 14, fontWeight: 800 }}>VS</div>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ color: "#6b7280", fontSize: 10, fontWeight: 700, marginBottom: 4 }}>BASELINE</div>
                      <div style={{ color: "#9ca3af", fontSize: 24, fontWeight: 900 }}>
                        {base != null ? format(base) : "Learning..."}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Grid for Visualization Widgets */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 32, flexWrap: "wrap" }}>
        
        {/* Visitor Dwell List */}
        <div style={{ ...glassStyle, padding: "24px 28px" }}>
          <div style={{ color: "#9ca3af", fontSize: 12, fontWeight: 700,
            textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 20 }}>
            Session Dwell Times
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {chartData.map((p, i) => (
              <div key={p.token_id}>
                <div style={{ display: "flex", justifyContent: "space-between",
                  marginBottom: 6, fontSize: 13 }}>
                  <span style={{ color: "#9ca3af", fontWeight: 600 }}>Visitor {i + 1}</span>
                  <span style={{ color: "#f9fafb", fontWeight: 700 }}>{dwellLabel(p.dwell_seconds)}</span>
                </div>
                <div style={{ background: "rgba(31, 41, 55, 0.4)", borderRadius: 6, height: 10, overflow: "hidden" }}>
                  <div style={{
                    height: "100%",
                    width: `${Math.min((p.dwell_seconds / (maxDwell * 1.2)) * 100, 100)}%`,
                    background: p.abandoned ? "linear-gradient(90deg, #f59e0b, #d97706)" : "linear-gradient(90deg, #10b981, #059669)",
                    borderRadius: 6, transition: "width 0.6s ease"
                  }} />
                </div>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", gap: 20, marginTop: 20 }}>
            {[["#10b981", "Served"], ["#f59e0b", "Left unattended"]].map(([c, l]) => (
              <div key={l} style={{ display: "flex", alignItems: "center",
                gap: 6, fontSize: 12, color: "#9ca3af" }}>
                <div style={{ width: 10, height: 10, borderRadius: 2, background: c }} />
                {l}
              </div>
            ))}
          </div>
        </div>

        {/* Hourly Traffic Distribution */}
        <div style={{ ...glassStyle, padding: "24px 28px" }}>
          <div style={{ color: "#9ca3af", fontSize: 12, fontWeight: 700,
            textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 20 }}>
            Traffic Profile By Hour
          </div>
          {hourly.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {hourly.map((h) => (
                <div key={h.hour}>
                  <div style={{ display: "flex", justifyContent: "space-between",
                    marginBottom: 6, fontSize: 13 }}>
                    <span style={{ color: "#9ca3af", fontWeight: 600 }}>
                      {h.hour}:00 – {h.hour + 1}:00 UTC
                    </span>
                    <span style={{ color: "#f9fafb", fontWeight: 700 }}>
                      {h.visitors} guest{h.visitors !== 1 ? "s" : ""} · avg {dwellLabel(h.avg_dwell_seconds)}
                    </span>
                  </div>
                  <div style={{ background: "rgba(31, 41, 55, 0.4)", borderRadius: 6, height: 10, overflow: "hidden" }}>
                    <div style={{
                      height: "100%",
                      width: `${Math.min((h.visitors / Math.max(...hourly.map(x => x.visitors))) * 100, 100)}%`,
                      background: "linear-gradient(90deg, #3b82f6, #1d4ed8)", borderRadius: 6, transition: "width 0.6s ease"
                    }} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ textAlign: "center", color: "#4b5563", padding: "40px 0" }}>No hourly distribution loaded</div>
          )}
        </div>
      </div>

      {/* Visitor Log Table */}
      <div style={{ ...glassStyle, padding: "24px 28px", marginBottom: 32 }}>
        <div style={{ color: "#9ca3af", fontSize: 12, fontWeight: 700,
          textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 20 }}>
          Detailed Entry Log
        </div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.08)" }}>
                {["Visitor ID", "Arrived At", "Camera", "Dwell Time", "Service Outcome"].map(h => (
                  <th key={h} style={{ textAlign: "left", padding: "12px 16px",
                    color: "#6b7280", fontWeight: 700, fontSize: 11,
                    textTransform: "uppercase", letterSpacing: 1 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {persons.map((p, i) => (
                <tr key={p.token_id} style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.04)" }}>
                  <td style={{ padding: "16px", color: "#f9fafb", fontWeight: 700 }}>
                    Visitor #{i + 1}
                  </td>
                  <td style={{ padding: "16px", color: "#9ca3af" }}>{formatTime(p.entered)}</td>
                  <td style={{ padding: "16px", color: "#9ca3af" }}>
                    {p.camera === "cam_01" ? "Entrance Cam" : p.camera}
                  </td>
                  <td style={{ padding: "16px", color: "#f9fafb", fontWeight: 700 }}>
                    {dwellLabel(p.dwell_seconds)}
                  </td>
                  <td style={{ padding: "16px" }}>
                    <span style={{
                      background: p.abandoned ? "rgba(239, 68, 68, 0.15)" : "rgba(16, 185, 129, 0.15)",
                      border: p.abandoned ? "1px solid rgba(239, 68, 68, 0.3)" : "1px solid rgba(16, 185, 129, 0.3)",
                      color: p.abandoned ? "#f87171" : "#4ade80",
                      padding: "4px 12px", borderRadius: 8, fontSize: 11, fontWeight: 700
                    }}>
                      {p.abandoned ? "Left unattended" : "Served"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Assistant Chat Console */}
      <div style={{ ...glassStyle, padding: "28px", background: "linear-gradient(145deg, rgba(17, 24, 39, 0.8), rgba(2, 6, 23, 0.8))" }}>
        <div style={{ color: "#9ca3af", fontSize: 12, fontWeight: 700,
          textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 6 }}>
          AI Assistant Chat
        </div>
        <p style={{ color: "#6b7280", fontSize: 13, margin: "0 0 20px" }}>
          Query your logs in plain conversational English. The assistant automatically incorporates historical baseline knowledge to detect anomalies.
        </p>

        {/* Preset Prompt Buttons */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 20 }}>
          {PRESET_QUESTIONS.map(q => (
            <button key={q} onClick={() => askQuestion(q)} style={{
              background: "rgba(31, 41, 55, 0.4)", border: "1px solid rgba(255, 255, 255, 0.06)",
              color: "#9ca3af", borderRadius: 12, padding: "8px 16px",
              fontSize: 12, cursor: "pointer", transition: "all 0.2s"
            }}>{q}</button>
          ))}
        </div>

        {/* Input area */}
        <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && askQuestion()}
            placeholder="Ask a question (e.g. 'How busy was Tuesday evening compared to usual?')"
            style={{
              flex: 1, background: "rgba(15, 23, 42, 0.6)", border: "1px solid rgba(255, 255, 255, 0.1)",
              borderRadius: 12, padding: "14px 20px", color: "#f9fafb",
              fontSize: 14, outline: "none", transition: "all 0.2s"
            }}
          />
          <button onClick={() => askQuestion()} disabled={loading} style={{
            background: "linear-gradient(135deg, #f59e0b, #d97706)", color: "#020617", border: "none",
            borderRadius: 12, padding: "14px 32px", fontWeight: 800,
            fontSize: 14, cursor: "pointer", opacity: loading ? 0.7 : 1, transition: "all 0.2s",
            boxShadow: "0 4px 14px rgba(245, 158, 11, 0.3)"
          }}>
            {loading ? "Thinking..." : "Query AI"}
          </button>
        </div>

        {/* Answer layout */}
        {answer && (
          <div style={{ background: "rgba(10, 15, 30, 0.5)", borderRadius: 16,
            padding: "24px", border: "1px solid rgba(96, 165, 250, 0.15)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div style={{ color: "#f59e0b", fontWeight: 800, fontSize: 13,
                textTransform: "uppercase", letterSpacing: 1.2 }}>Response</div>
              {answer.sql && (
                <span style={{ fontSize: 11, color: "#4b5563", fontFamily: "monospace" }}>
                  SQL: {answer.sql.length > 50 ? answer.sql.slice(0, 50) + "..." : answer.sql}
                </span>
              )}
            </div>
            
            <div style={{ color: "#f9fafb", fontSize: 15, lineHeight: 1.7, marginBottom: 18 }}>
              {answer.plain_answer}
            </div>

            {/* Answer Feedbacks */}
            {answer.answer_id && (
              <div style={{ display: "flex", alignItems: "center", gap: 14,
                borderTop: "1px solid rgba(255, 255, 255, 0.06)", paddingTop: 16 }}>
                <span style={{ color: "#6b7280", fontSize: 12 }}>
                  Helpful response?
                </span>
                <button
                  onClick={() => rateAnswer(answer.answer_id, 1)}
                  disabled={!!ratings[answer.answer_id]}
                  style={{
                    background: ratings[answer.answer_id] === 1 ? "rgba(16, 185, 129, 0.2)" : "rgba(31, 41, 55, 0.4)",
                    border: `1px solid ${ratings[answer.answer_id] === 1 ? "#10b981" : "rgba(255,255,255,0.08)"}`,
                    color: ratings[answer.answer_id] === 1 ? "#4ade80" : "#9ca3af",
                    borderRadius: 8, padding: "6px 14px", fontSize: 13,
                    cursor: ratings[answer.answer_id] ? "default" : "pointer",
                    transition: "all 0.2s"
                  }}
                >👍 Yes</button>
                <button
                  onClick={() => rateAnswer(answer.answer_id, -1)}
                  disabled={!!ratings[answer.answer_id]}
                  style={{
                    background: ratings[answer.answer_id] === -1 ? "rgba(239, 68, 68, 0.2)" : "rgba(31, 41, 55, 0.4)",
                    border: `1px solid ${ratings[answer.answer_id] === -1 ? "#ef4444" : "rgba(255,255,255,0.08)"}`,
                    color: ratings[answer.answer_id] === -1 ? "#f87171" : "#9ca3af",
                    borderRadius: 8, padding: "6px 14px", fontSize: 13,
                    cursor: ratings[answer.answer_id] ? "default" : "pointer",
                    transition: "all 0.2s"
                  }}
                >👎 No</button>
                {ratings[answer.answer_id] === 1 && (
                  <span style={{ color: "#4ade80", fontSize: 12, fontWeight: 500 }}>
                    ✓ Logged to few-shot memory pool.
                  </span>
                )}
                {ratings[answer.answer_id] === -1 && (
                  <span style={{ color: "#f87171", fontSize: 12, fontWeight: 500 }}>
                    ✗ Answer flagged for correction.
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [screen, setScreen] = useState("upload");
  const [jobId, setJobId] = useState(null);

  return screen === "upload" ? (
    <UploadScreen onProcessingStart={(id) => { setJobId(id); setScreen("processing"); }} />
  ) : screen === "processing" ? (
    <ProcessingScreen jobId={jobId} onComplete={() => setScreen("dashboard")} />
  ) : (
    <DashboardScreen onReset={() => { setJobId(null); setScreen("upload"); }} />
  );
}
