import { useState, useEffect, useCallback, useRef } from 'react'
import Navbar from './components/Navbar'
import Hero from './components/Hero'
import UploadSection from './components/UploadSection'
import ProgressSection from './components/ProgressSection'
import ResultsSection from './components/ResultsSection'
import Toast from './components/Toast'
import { uploadVideo, fetchReport, checkVlm, createProgressStream } from './api'

// App-level view states
const VIEW = { UPLOAD: 'upload', PROGRESS: 'progress', RESULTS: 'results' }

let toastIdCounter = 0

export default function App() {
  const [view,        setView]      = useState(VIEW.UPLOAD)
  const [jobId,       setJobId]     = useState(null)
  const [progress,    setProgress]  = useState({ percent: 0, message: '', logs: [] })
  const [report,      setReport]    = useState(null)
  const [vlmAvail,    setVlmAvail]  = useState(false)
  const [toasts,      setToasts]    = useState([])
  const cleanupSseRef = useRef(null)

  // ── VLM status check on mount ────────────────────────────────────────────
  useEffect(() => {
    checkVlm().then(d => setVlmAvail(d.vlm_available === true))
  }, [])

  // ── Scroll to section whenever view changes ──────────────────────────────
  useEffect(() => {
    const ids = { [VIEW.UPLOAD]: 'upload', [VIEW.PROGRESS]: 'progress', [VIEW.RESULTS]: 'results' }
    const el = document.getElementById(ids[view])
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [view])

  // ── Toast helpers ────────────────────────────────────────────────────────
  const addToast = useCallback((message, type = 'info') => {
    const id = ++toastIdCounter
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000)
  }, [])

  // ── Upload + analysis flow ───────────────────────────────────────────────
  async function handleAnalyze(file, useVlm) {
    try {
      addToast('Uploading video…', 'info')
      setProgress({ percent: 0, message: 'Uploading video to server…', logs: [] })
      setView(VIEW.PROGRESS)
      const { job_id } = await uploadVideo(file, useVlm, (percent) => {
        setProgress(prev => {
          // Avoid spamming the log block with exact duplicates, but keep a readable log state
          const msg = `Uploading: ${percent}%`
          const lastLog = prev.logs[prev.logs.length - 1]
          return {
            percent,
            message: 'Uploading video to server…',
            logs: (lastLog && lastLog.startsWith('Uploading:')) 
              ? [...prev.logs.slice(0, -1), msg] // replace last log if it's an upload progress log
              : [...prev.logs, msg]
          }
        })
      })
      setJobId(job_id)
      setProgress({ percent: 0, message: 'Starting analysis…', logs: [] })
      addToast('Upload successful! Analysis started.', 'success')
      startStreaming(job_id)
    } catch (err) {
      addToast(`Upload failed: ${err.message}`, 'error')
      resetToUpload()
      throw err   // re-throw so UploadSection can re-enable button
    }
  }

  function startStreaming(jobId) {
    // Clean up any existing SSE connection
    if (cleanupSseRef.current) cleanupSseRef.current()

    const now = () => new Date().toLocaleTimeString()

    const cleanup = createProgressStream(
      jobId,
      // onMessage
      (data) => {
        setProgress(prev => ({
          percent: data.percent ?? prev.percent,
          message: data.message ?? prev.message,
          logs: data.message
            ? [...prev.logs, `[${now()}] ${data.message}`]
            : prev.logs,
        }))
      },
      // onDone
      () => {
        addToast('Analysis complete! Loading report…', 'success')
        loadReport(jobId)
      },
      // onError — fallback to polling
      (errMsg) => {
        addToast(`Stream interrupted — polling for results…`, 'warn')
        pollForReport(jobId)
      }
    )
    cleanupSseRef.current = cleanup
  }

  async function loadReport(jobId) {
    try {
      const data = await fetchReport(jobId)
      setReport(data)
      setView(VIEW.RESULTS)
      addToast('Report ready! 🎉', 'success')
    } catch (err) {
      addToast(`Could not load report: ${err.message}`, 'error')
      resetToUpload()
    }
  }

  async function pollForReport(jobId) {
    for (let i = 0; i < 60; i++) {        // max 5 min polling
      await new Promise(r => setTimeout(r, 5000))
      try {
        const res = await fetch(`/api/report/${jobId}`)
        if (res.status === 200) {
          const data = await res.json()
          setReport(data)
          setView(VIEW.RESULTS)
          addToast('Report ready! 🎉', 'success')
          return
        }
      } catch { /* keep trying */ }
    }
    addToast('Analysis timed out. Please try again.', 'error')
    resetToUpload()
  }

  function resetToUpload() {
    if (cleanupSseRef.current) { cleanupSseRef.current(); cleanupSseRef.current = null }
    setView(VIEW.UPLOAD)
    setJobId(null)
    setReport(null)
    setProgress({ percent: 0, message: '', logs: [] })
  }

  // ── Navbar shadow on scroll ──────────────────────────────────────────────
  useEffect(() => {
    const handler = () => {
      const nav = document.querySelector('nav')
      if (nav) nav.style.boxShadow = window.scrollY > 10
        ? '0 4px 20px rgba(0,0,0,0.09)'
        : '0 1px 3px rgba(0,0,0,0.06)'
    }
    window.addEventListener('scroll', handler, { passive: true })
    return () => window.removeEventListener('scroll', handler)
  }, [])

  return (
    <>
      <Navbar showResults={view === VIEW.RESULTS} vlmAvailable={vlmAvail} />

      <Hero />

      {/* Upload — always mounted, hidden when not active */}
      <div style={{ display: view === VIEW.UPLOAD ? 'block' : 'none' }}>
        <UploadSection onAnalyze={handleAnalyze} />
      </div>

      {/* Progress */}
      {view === VIEW.PROGRESS && (
        <ProgressSection progress={progress} />
      )}

      {/* Results */}
      {view === VIEW.RESULTS && report && (
        <ResultsSection
          data={report}
          jobId={jobId}
          onReset={resetToUpload}
        />
      )}

      <footer style={{
        background: 'var(--surface)',
        borderTop: '1px solid var(--border)',
        padding: '20px 0',
        marginTop: '40px',
      }}>
        <div className="container" style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '8px',
          fontSize: '0.82rem',
          color: 'var(--text-muted)',
        }}>
          <span>🗑️ <strong>TrashGuard</strong> — Trash Detection Video Analytics</span>
          <span>Powered by YOLO · BoT-SORT · nanoVLM</span>
        </div>
      </footer>

      <Toast toasts={toasts} />
    </>
  )
}
