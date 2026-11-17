import { useEffect, useState } from "react";
import { Activity, AlertTriangle, ArrowUpRight, CheckCircle2, ChevronRight, Code2, Github, LoaderCircle, LockKeyhole, ScanSearch, ShieldCheck, Terminal } from "lucide-react";

type Finding = { rule_id: string; severity: "high" | "medium" | "low"; title: string; file: string; line: number; evidence: string; recommendation: string };
type Review = { id: string; repository: string; repository_url: string; branch: string; files_analyzed: number; ai_enabled: boolean; ai_error?: string | null; summary: { total: number; high: number; medium: number; low: number }; findings: Finding[] };

export default function App() {
  const [url, setUrl] = useState("");
  const [review, setReview] = useState<Review | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");
  const [aiAvailable, setAiAvailable] = useState(false);
  const [useAI, setUseAI] = useState(false);

  useEffect(() => {
    fetch("/api/health").then(response => response.ok ? response.json() : null).then(data => setAiAvailable(Boolean(data?.ai_available))).catch(() => setAiAvailable(false));
  }, []);

  async function runReview(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true); setError(""); setReview(null);
    try {
      const response = await fetch("/api/reviews", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ repository_url: url, use_ai: useAI }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Review request failed.");
      setReview(data);
    } catch (e) { setError(e instanceof Error ? e.message : "Unexpected error. Try again."); }
    finally { setLoading(false); }
  }

  const findings = review?.findings.filter(f => filter === "all" || f.severity === filter) ?? [];

  return <main className="shell">
    <header className="topbar">
      <a className="brand" href="#"><span className="brand-mark"><ShieldCheck size={19}/></span> sentinel<span>review</span></a>
      <div className="top-meta"><span className="live-dot"/> ANALYSIS ENGINE <b>V0.1</b><a href="https://github.com/deepmodak79/sentinel-review" target="_blank" rel="noreferrer" aria-label="GitHub repository"><Github size={17}/></a></div>
    </header>

    <section className="hero">
      <div className="eyebrow"><span/> CODE INTELLIGENCE / SECURITY REVIEW</div>
      <h1>Know what your code<br/><em>is really doing.</em></h1>
      <p className="hero-copy">A second set of eyes for your repository. Surface risky patterns, inspect evidence, and decide what deserves attention.</p>
      <form className="scan-form" onSubmit={runReview}>
        <div className="input-wrap"><Github size={18}/><input aria-label="Public GitHub repository URL" placeholder="https://github.com/owner/repository" value={url} onChange={e => setUrl(e.target.value)} required type="url"/></div>
        <button disabled={loading}>{loading ? <><LoaderCircle className="spin" size={16}/> SCANNING</> : <><ScanSearch size={16}/> REVIEW REPOSITORY <ArrowUpRight size={15}/></>}</button>
      </form>
      <div className="form-note"><LockKeyhole size={13}/> Public repositories only · Read-only analysis · No code is modified</div>
      <label className={`ai-opt-in ${!aiAvailable ? "unavailable" : ""}`}><input type="checkbox" checked={useAI} disabled={!aiAvailable || loading} onChange={event => setUseAI(event.target.checked)}/><span><b>Include Gemini-assisted review</b><small>{aiAvailable ? "Sends bounded source excerpts, with common credential patterns redacted, to Google Gemini. Optional; off by default." : "Unavailable until GEMINI_API_KEY is configured on the server. Deterministic checks work without it."}</small></span></label>
      {error && <div className="error" role="alert"><AlertTriangle size={16}/>{error}</div>}
    </section>

    {review ? <section className="results" aria-live="polite">
      <div className="result-head"><div><div className="section-kicker">REVIEW COMPLETE</div><h2>{review.repository}</h2><p><a href={review.repository_url} target="_blank" rel="noreferrer">{review.repository_url} <ArrowUpRight size={12}/></a> <span>·</span> {review.branch} branch <span>·</span> {review.files_analyzed} files inspected</p></div><div className="complete"><CheckCircle2 size={15}/> ANALYSIS FINISHED</div></div>
      <div className="metrics">
        <div className="metric total"><span>FINDINGS</span><strong>{review.summary.total}</strong><small>All detected patterns</small></div>
        <div className="metric high"><span>HIGH</span><strong>{review.summary.high}</strong><small>Prioritize these first</small></div>
        <div className="metric medium"><span>MEDIUM</span><strong>{review.summary.medium}</strong><small>Review in context</small></div>
        <div className="metric low"><span>LOW</span><strong>{review.summary.low}</strong><small>Worth a cleanup pass</small></div>
      </div>
      <div className="findings-head"><div><div className="section-kicker">EVIDENCE REGISTER</div><h3>Findings <span>{findings.length}</span></h3></div><div className="filters">{["all","high","medium","low"].map(x=><button key={x} className={filter===x?"selected":""} onClick={()=>setFilter(x)}>{x.toUpperCase()}</button>)}</div></div>
      {findings.length ? <div className="finding-list">{findings.map((f,i)=><article className="finding" key={f.rule_id+f.file+f.line+i}>
        <div className="finding-top"><span className={"severity "+f.severity}>{f.severity}</span><code>{f.rule_id}</code><span className="file">{f.file}:{f.line}</span></div>
        <h4>{f.title}</h4><pre>{f.evidence}</pre><p><b>RECOMMENDATION</b> {f.recommendation}</p>
      </article>)}</div> : <div className="empty"><CheckCircle2 size={22}/><h4>No findings in this severity</h4><p>Try another filter or review a different repository.</p></div>}
      <p className="disclaimer">{review.ai_enabled ? "Gemini-assisted review was included. AI findings are advisory and may be incorrect." : review.ai_error ? `Gemini review could not complete: ${review.ai_error} Deterministic results are still available.` : "Static pattern checks can produce false positives and cannot prove a vulnerability. Validate every finding before acting."}</p>
    </section> : <section className="below">
      <div className="below-title"><span>THE REVIEW SURFACE</span><span>BUILT FOR SIGNAL, NOT NOISE</span></div>
      <div className="feature-grid">
        <article><div className="feature-icon"><Terminal size={18}/></div><h3>Evidence first</h3><p>Every deterministic finding points to a file, line, and matched code snippet.</p></article>
        <article><div className="feature-icon"><Activity size={18}/></div><h3>Risk, ranked</h3><p>High, medium, and low severity help you focus on the most consequential patterns.</p></article>
        <article><div className="feature-icon"><Code2 size={18}/></div><h3>Read-only by design</h3><p>SentinelReview inspects public source. It never pushes changes or merges pull requests.</p></article>
      </div>
      <div className="engine-note"><div><span className="engine-pulse"/><b>DETERMINISTIC ENGINE</b><small>Available now</small></div><div><span className={aiAvailable ? "engine-pulse" : "engine-idle"}/><b>AI REVIEW</b><small>{aiAvailable ? "Available · opt in above" : "Optional · configure Gemini key on server"}</small></div><ChevronRight size={17}/></div>
    </section>}

    <footer><span>© 2026 SENTINELREVIEW</span><span>BUILT TO MAKE CODE SAFER, ONE REVIEW AT A TIME.</span><a href="https://github.com/deepmodak79/sentinel-review" target="_blank" rel="noreferrer">SOURCE CODE <ArrowUpRight size={12}/></a></footer>
  </main>;
}
