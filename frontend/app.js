/**
 * app.js — TrashGuard Frontend Logic
 * Handles upload, SSE progress, report rendering, gallery, CSV download, print.
 */

const API = "http://localhost:5000/api";

// ── State ─────────────────────────────────────────────────────────────────
let currentJobId = null;
let reportData = null;
let galleryFrames = [];
let galleryIndex = 0;
let sseSource = null;

// ── DOM refs ──────────────────────────────────────────────────────────────
const dropZone       = document.getElementById("drop-zone");
const fileInput      = document.getElementById("file-input");
const browseBtn      = document.getElementById("browse-btn");
const filePreview    = document.getElementById("file-preview");
const fileName       = document.getElementById("file-name");
const fileSize       = document.getElementById("file-size");
const analyzeBtn     = document.getElementById("analyze-btn");
const analyzeBtnLbl  = document.getElementById("analyze-btn-label");
const clearFileBtn   = document.getElementById("clear-file-btn");
const vlmToggle      = document.getElementById("vlm-toggle");

const progressSection  = document.getElementById("progress-section");
const progressMsg      = document.getElementById("progress-msg");
const progressPct      = document.getElementById("progress-pct");
const progressBar      = document.getElementById("progress-bar");
const progressLog      = document.getElementById("progress-log");

const resultsSection   = document.getElementById("results-section");
const reportMeta       = document.getElementById("report-meta");
const navResults       = document.getElementById("nav-results");
const csvBtn           = document.getElementById("csv-btn");
const printBtn         = document.getElementById("print-btn");
const newAnalysisBtn   = document.getElementById("new-analysis-btn");

const eventsListEl     = document.getElementById("events-list");
const eventsCountBadge = document.getElementById("events-count-badge");
const vlmListEl        = document.getElementById("vlm-list");
const vlmCountBadge    = document.getElementById("vlm-count-badge");
const galleryWrap      = document.getElementById("gallery-wrap");
const galleryThumbs    = document.getElementById("gallery-thumbnails");
const galleryCounter   = document.getElementById("gallery-counter");
const galPrev          = document.getElementById("gal-prev");
const galNext          = document.getElementById("gal-next");
const classBarsEl      = document.getElementById("class-bars");
const tracksTbody      = document.getElementById("tracks-tbody");
const printableReport  = document.getElementById("printable-report");

// Stat card values
const scDuration  = document.getElementById("sc-duration-val");
const scPersons   = document.getElementById("sc-persons-val");
const scVehicles  = document.getElementById("sc-vehicles-val");
const scTrash     = document.getElementById("sc-trash-val");
const scEvents    = document.getElementById("sc-events-val");
const scFps       = document.getElementById("sc-fps-val");

// ── Helpers ───────────────────────────────────────────────────────────────
function fmtBytes(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function fmtDuration(sec) {
  const m = Math.floor(sec / 60);
  const s = (sec % 60).toFixed(1);
  return `${m}m ${s}s`;
}

function showToast(msg, type = "info") {
  const icons = { success: "✅", error: "❌", info: "ℹ️", warn: "⚠️" };
  const tc = document.getElementById("toast-container");
  const el = document.createElement("div");
  el.className = `toast toast--${type}`;
  el.innerHTML = `<span>${icons[type] || "ℹ️"}</span><span>${msg}</span>`;
  tc.appendChild(el);
  setTimeout(() => el.style.opacity = "0", 3500);
  setTimeout(() => el.remove(), 3800);
}

function scrollToSection(id) {
  document.getElementById(id).scrollIntoView({ behavior: "smooth", block: "start" });
}

// ── Check VLM availability ────────────────────────────────────────────────
async function checkVlm() {
  try {
    const r = await fetch(`${API}/vlmcheck`);
    const d = await r.json();
    const badge = document.getElementById("vlm-badge");
    if (!d.vlm_available) {
      badge.textContent = "VLM Unavailable";
      badge.style.background = "#fff7ed";
      badge.style.color = "#f59e0b";
      badge.style.borderColor = "rgba(245,158,11,0.2)";
    }
  } catch {
    /* server not running yet — ignore */
  }
}

// ── Drag & drop ───────────────────────────────────────────────────────────
dropZone.addEventListener("click", () => fileInput.click());
browseBtn.addEventListener("click", (e) => { e.stopPropagation(); fileInput.click(); });

dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("drag-over");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file) handleFileSelected(file);
});

fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) handleFileSelected(fileInput.files[0]);
});

clearFileBtn.addEventListener("click", resetUpload);

function handleFileSelected(file) {
  const allowed = ["video/mp4","video/avi","video/quicktime","video/x-matroska",
                   "video/webm","video/x-msvideo","video/x-ms-wmv","video/mp2t"];
  const ext = file.name.split(".").pop().toLowerCase();
  const allowedExt = ["mp4","avi","mov","mkv","webm","m4v"];
  if (!allowedExt.includes(ext)) {
    showToast("Unsupported file type. Use MP4, AVI, MOV, MKV, or WebM.", "error");
    return;
  }
  fileName.textContent = file.name;
  fileSize.textContent = fmtBytes(file.size);
  filePreview.classList.remove("hidden");
  filePreview._file = file;
  dropZone.classList.add("hidden");
}

function resetUpload() {
  filePreview._file = null;
  fileInput.value = "";
  filePreview.classList.add("hidden");
  dropZone.classList.remove("hidden");
  analyzeBtnLbl.textContent = "Start Analysis";
  analyzeBtn.disabled = false;
}

// ── Upload & analyse ──────────────────────────────────────────────────────
analyzeBtn.addEventListener("click", startAnalysis);

async function startAnalysis() {
  const file = filePreview._file;
  if (!file) { showToast("Please select a video file first.", "warn"); return; }

  analyzeBtnLbl.textContent = "Uploading…";
  analyzeBtn.disabled = true;

  const formData = new FormData();
  formData.append("video", file);
  formData.append("use_vlm", vlmToggle.checked ? "true" : "false");

  try {
    const resp = await fetch(`${API}/upload`, { method: "POST", body: formData });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.error || "Upload failed");
    }
    const { job_id } = await resp.json();
    currentJobId = job_id;
    showProgress();
    listenProgress(job_id);
  } catch (e) {
    showToast(`Upload error: ${e.message}`, "error");
    analyzeBtnLbl.textContent = "Start Analysis";
    analyzeBtn.disabled = false;
  }
}

// ── Progress streaming (SSE) ──────────────────────────────────────────────
function showProgress() {
  document.getElementById("upload-section").classList.add("hidden");
  progressSection.classList.remove("hidden");
  progressLog.innerHTML = "";
  progressBar.style.width = "0%";
  progressPct.textContent = "0%";
  scrollToSection("progress-section");
}

function listenProgress(jobId) {
  if (sseSource) sseSource.close();
  sseSource = new EventSource(`${API}/status/${jobId}`);

  sseSource.onmessage = (e) => {
    const data = JSON.parse(e.data);

    // Update bar
    const pct = data.percent ?? 0;
    progressBar.style.width = pct + "%";
    progressPct.textContent = Math.round(pct) + "%";
    progressMsg.textContent = data.message || "Processing…";

    // Append log entry
    const entry = document.createElement("div");
    entry.className = "log-entry";
    entry.textContent = `[${new Date().toLocaleTimeString()}] ${data.message || ""}`;
    progressLog.appendChild(entry);
    progressLog.scrollTop = progressLog.scrollHeight;

    if (data.status === "done") {
      sseSource.close();
      fetchReport(jobId);
    } else if (data.status === "error") {
      sseSource.close();
      showToast(`Analysis failed: ${data.error || "Unknown error"}`, "error");
      resetToUpload();
    }
  };

  sseSource.onerror = () => {
    sseSource.close();
    // Fallback: poll
    pollStatus(jobId);
  };
}

async function pollStatus(jobId) {
  while (true) {
    await new Promise(r => setTimeout(r, 2000));
    try {
      const r = await fetch(`${API}/report/${jobId}`);
      if (r.status === 200) { fetchReport(jobId); break; }
      if (r.status >= 500) { showToast("Server error during analysis.", "error"); break; }
    } catch { /* keep polling */ }
  }
}

async function fetchReport(jobId) {
  try {
    const r = await fetch(`${API}/report/${jobId}`);
    if (!r.ok) throw new Error("Report not ready");
    reportData = await r.json();
    showResults();
  } catch (e) {
    showToast(`Could not load report: ${e.message}`, "error");
    resetToUpload();
  }
}

// ── Results rendering ─────────────────────────────────────────────────────
function showResults() {
  progressSection.classList.add("hidden");
  resultsSection.classList.remove("hidden");
  navResults.classList.remove("hidden");
  scrollToSection("results-section");
  renderReport();
}

function renderReport() {
  const d = reportData;

  // Meta
  reportMeta.textContent = `Generated: ${d.generated_at} · ${d.width}×${d.height} · ${d.fps} fps`;

  // Stat cards
  scDuration.textContent = fmtDuration(d.duration_sec);
  scPersons.textContent  = d.unique_persons;
  scVehicles.textContent = d.unique_cars;
  scTrash.textContent    = d.unique_trash;
  scEvents.textContent   = d.total_events;
  scFps.textContent      = d.fps;

  // Animate stat cards
  document.querySelectorAll(".stat-card").forEach((el, i) => {
    el.style.animationDelay = `${i * 0.07}s`;
  });

  // Littering events
  renderEvents(d.throwing_events);

  // VLM descriptions
  renderVlm(d.vlm_descriptions);

  // Detection breakdown
  renderClassBars(d.class_counts);

  // Tracks table
  renderTracksTable(d.track_timeline);

  // Load gallery frames
  loadGallery();

  // Printable report
  buildPrintableReport(d);

  showToast("Analysis complete! 🎉", "success");
}

function renderEvents(events) {
  eventsCountBadge.textContent = events.length;
  if (!events.length) {
    eventsListEl.innerHTML = `<div class="empty-state">✅ No littering events detected in this video.</div>`;
    return;
  }
  eventsListEl.innerHTML = "";
  events.forEach((ev, i) => {
    const el = document.createElement("div");
    el.className = "event-item";
    el.innerHTML = `
      <div class="event-num">${i + 1}</div>
      <div>
        <div class="event-time">⏱ ${ev.time_formatted}</div>
        <div class="event-desc">${escapeHtml(ev.description)}</div>
      </div>`;
    eventsListEl.appendChild(el);
  });
}

function renderVlm(vlms) {
  vlmCountBadge.textContent = vlms.length;
  if (!vlms.length) {
    vlmListEl.innerHTML = `<div class="empty-state">VLM descriptions not available or disabled.</div>`;
    return;
  }
  vlmListEl.innerHTML = "";
  vlms.forEach(vd => {
    const el = document.createElement("div");
    el.className = "vlm-item";
    el.innerHTML = `
      <div class="vlm-time">🔍 ${vd.time_formatted}</div>
      <div class="vlm-desc">${escapeHtml(vd.description)}</div>`;
    vlmListEl.appendChild(el);
  });
}

function renderClassBars(counts) {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  if (!entries.length) {
    classBarsEl.innerHTML = `<div class="empty-state">No detections.</div>`;
    return;
  }
  const max = entries[0][1];
  classBarsEl.innerHTML = "";
  const colorMap = {
    person: "#10b981", car: "#3b82f6", truck: "#3b82f6",
    bus: "#3b82f6", bicycle: "#8b5cf6", motorcycle: "#8b5cf6",
  };
  entries.forEach(([cls, cnt]) => {
    const pct = Math.round((cnt / max) * 100);
    const color = colorMap[cls] || "#ef4444";
    const row = document.createElement("div");
    row.className = "class-bar-row";
    row.innerHTML = `
      <div class="class-bar-label">
        <span class="class-bar-name">${cls}</span>
        <span class="class-bar-count">${cnt.toLocaleString()}</span>
      </div>
      <div class="class-bar-track">
        <div class="class-bar-fill" style="background:${color};width:0%" data-pct="${pct}"></div>
      </div>`;
    classBarsEl.appendChild(row);
  });
  // Animate bars after paint
  requestAnimationFrame(() => {
    document.querySelectorAll(".class-bar-fill").forEach(el => {
      el.style.width = el.dataset.pct + "%";
    });
  });
}

function renderTracksTable(tracks) {
  if (!tracks.length) {
    tracksTbody.innerHTML = `<tr><td colspan="6" class="empty-state">No tracks.</td></tr>`;
    return;
  }
  const sorted = [...tracks].sort((a, b) => a.class_name.localeCompare(b.class_name));
  tracksTbody.innerHTML = sorted.map(t => {
    const cls = t.class_name;
    let badgeClass = "track-custom";
    if (cls === "person") badgeClass = "track-person";
    else if (["car","truck","bus","bicycle","motorcycle"].includes(cls)) badgeClass = "track-car";
    else badgeClass = "track-trash";

    const model = t.source_model === "custom"
      ? `<span class="badge badge--warn" style="font-size:0.7rem">custom</span>`
      : `<span class="badge badge--blue" style="font-size:0.7rem">base</span>`;

    return `<tr>
      <td><strong>#${t.track_id}</strong></td>
      <td><span class="track-badge ${badgeClass}">${cls}</span></td>
      <td>${model}</td>
      <td><code style="font-size:0.78rem">${t.first_seen_fmt}</code></td>
      <td><code style="font-size:0.78rem">${t.last_seen_fmt}</code></td>
      <td>${t.detections.toLocaleString()}</td>
    </tr>`;
  }).join("");
}

// ── Gallery ───────────────────────────────────────────────────────────────
async function loadGallery() {
  try {
    const r = await fetch(`${API}/frames/${currentJobId}`);
    const d = await r.json();
    galleryFrames = d.frames || [];
    galleryIndex = 0;
    renderGallery();
  } catch (e) {
    galleryWrap.innerHTML = `<div class="empty-state">Frame gallery unavailable.</div>`;
  }
}

function renderGallery() {
  if (!galleryFrames.length) {
    galleryWrap.innerHTML = `<div class="empty-state" style="color:#aaa">No annotated frames available.</div>`;
    galleryCounter.textContent = "0 / 0";
    galleryThumbs.innerHTML = "";
    return;
  }

  // Main image
  const idx = galleryFrames[galleryIndex];
  const src = `${API}/frame/${currentJobId}/${idx}`;
  galleryWrap.innerHTML = `<img src="${src}" alt="Frame ${idx}" loading="lazy"/>`;
  galleryCounter.textContent = `${galleryIndex + 1} / ${galleryFrames.length}`;

  // Thumbnails (show max 12)
  const thumbsToShow = galleryFrames.slice(0, 12);
  galleryThumbs.innerHTML = thumbsToShow.map((fi, ti) => `
    <div class="gallery-thumb ${ti === galleryIndex ? 'active' : ''}" data-ti="${ti}">
      <img src="${API}/frame/${currentJobId}/${fi}" alt="thumb" loading="lazy"/>
    </div>`).join("");

  galleryThumbs.querySelectorAll(".gallery-thumb").forEach(el => {
    el.addEventListener("click", () => {
      galleryIndex = parseInt(el.dataset.ti);
      renderGallery();
    });
  });
}

galPrev.addEventListener("click", () => {
  if (!galleryFrames.length) return;
  galleryIndex = (galleryIndex - 1 + galleryFrames.length) % galleryFrames.length;
  renderGallery();
});
galNext.addEventListener("click", () => {
  if (!galleryFrames.length) return;
  galleryIndex = (galleryIndex + 1) % galleryFrames.length;
  renderGallery();
});

// ── Printable report builder ─────────────────────────────────────────────
function buildPrintableReport(d) {
  const eventsHtml = d.throwing_events.length
    ? d.throwing_events.map((ev, i) => `
        <tr>
          <td>${i + 1}</td>
          <td>${ev.time_formatted}</td>
          <td>${ev.timestamp.toFixed(3)}s</td>
          <td>#${ev.person_track_id}</td>
          <td>#${ev.trash_track_id}</td>
          <td>${escapeHtml(ev.description)}</td>
        </tr>`).join("")
    : `<tr><td colspan="6" style="text-align:center;color:#888">No events detected</td></tr>`;

  const vlmHtml = d.vlm_descriptions.length
    ? d.vlm_descriptions.map(vd => `
        <tr>
          <td>${vd.time_formatted}</td>
          <td>${escapeHtml(vd.description)}</td>
        </tr>`).join("")
    : `<tr><td colspan="2" style="text-align:center;color:#888">N/A</td></tr>`;

  printableReport.innerHTML = `
    <h1 style="font-size:1.6rem;font-weight:800;margin-bottom:4px">🗑️ TrashGuard — Incident Analysis Report</h1>
    <p style="color:#6b7280;margin-bottom:24px">Generated: ${d.generated_at}</p>

    <h2 style="font-size:1.1rem;margin-bottom:10px;border-bottom:2px solid #e4e8f0;padding-bottom:6px">Video Information</h2>
    <table style="width:100%;border-collapse:collapse;margin-bottom:24px;font-size:0.88rem">
      <tr><td style="padding:5px 0;font-weight:600;width:200px">File</td><td>${escapeHtml(d.video_path)}</td></tr>
      <tr><td style="padding:5px 0;font-weight:600">Duration</td><td>${fmtDuration(d.duration_sec)}</td></tr>
      <tr><td style="padding:5px 0;font-weight:600">Resolution</td><td>${d.width} × ${d.height}</td></tr>
      <tr><td style="padding:5px 0;font-weight:600">Frame Rate</td><td>${d.fps} fps</td></tr>
      <tr><td style="padding:5px 0;font-weight:600">Total Frames</td><td>${d.total_frames.toLocaleString()}</td></tr>
    </table>

    <h2 style="font-size:1.1rem;margin-bottom:10px;border-bottom:2px solid #e4e8f0;padding-bottom:6px">Detection Summary</h2>
    <table style="width:100%;border-collapse:collapse;margin-bottom:24px;font-size:0.88rem">
      <tr><td style="padding:5px 0;font-weight:600;width:200px">Persons Tracked</td><td>${d.unique_persons}</td></tr>
      <tr><td style="padding:5px 0;font-weight:600">Vehicles Tracked</td><td>${d.unique_cars}</td></tr>
      <tr><td style="padding:5px 0;font-weight:600">Trash Items Detected</td><td>${d.unique_trash}</td></tr>
      <tr><td style="padding:5px 0;font-weight:600;color:#ef4444">⚠ Littering Events</td><td style="color:#ef4444;font-weight:700">${d.total_events}</td></tr>
    </table>

    <h2 style="font-size:1.1rem;margin-bottom:10px;border-bottom:2px solid #e4e8f0;padding-bottom:6px">Littering / Throwing Events</h2>
    <table style="width:100%;border-collapse:collapse;margin-bottom:24px;font-size:0.82rem">
      <thead><tr style="background:#f1f3f9">
        <th style="padding:8px;text-align:left">#</th>
        <th style="padding:8px;text-align:left">Time</th>
        <th style="padding:8px;text-align:left">Seconds</th>
        <th style="padding:8px;text-align:left">Person</th>
        <th style="padding:8px;text-align:left">Trash</th>
        <th style="padding:8px;text-align:left">Description</th>
      </tr></thead>
      <tbody>${eventsHtml}</tbody>
    </table>

    <h2 style="font-size:1.1rem;margin-bottom:10px;border-bottom:2px solid #e4e8f0;padding-bottom:6px">VLM Scene Descriptions</h2>
    <table style="width:100%;border-collapse:collapse;margin-bottom:24px;font-size:0.82rem">
      <thead><tr style="background:#f1f3f9">
        <th style="padding:8px;text-align:left;width:100px">Time</th>
        <th style="padding:8px;text-align:left">Description</th>
      </tr></thead>
      <tbody>${vlmHtml}</tbody>
    </table>
  `;
}

// ── Export actions ─────────────────────────────────────────────────────────
csvBtn.addEventListener("click", () => {
  if (!currentJobId) return;
  const a = document.createElement("a");
  a.href = `${API}/download/csv/${currentJobId}`;
  a.download = `trash_report_${currentJobId.slice(0,8)}.csv`;
  a.click();
  showToast("CSV download started.", "success");
});

printBtn.addEventListener("click", () => {
  window.print();
});

newAnalysisBtn.addEventListener("click", resetToUpload);

function resetToUpload() {
  currentJobId = null;
  reportData = null;
  galleryFrames = [];
  galleryIndex = 0;
  if (sseSource) { sseSource.close(); sseSource = null; }

  progressSection.classList.add("hidden");
  resultsSection.classList.add("hidden");
  navResults.classList.add("hidden");
  document.getElementById("upload-section").classList.remove("hidden");
  resetUpload();
  scrollToSection("upload-section");
}

// ── Utils ─────────────────────────────────────────────────────────────────
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Init ──────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  checkVlm();

  // Smooth navbar shadow on scroll
  const navbar = document.getElementById("navbar");
  window.addEventListener("scroll", () => {
    navbar.style.boxShadow = window.scrollY > 10
      ? "0 4px 20px rgba(0,0,0,0.09)"
      : "0 1px 3px rgba(0,0,0,0.06)";
  });

  // Animate stat cards stagger delay
  document.querySelectorAll(".stat-card").forEach((el, i) => {
    el.style.animationDelay = `${i * 0.08}s`;
  });
});
