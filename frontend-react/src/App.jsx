import { useState, useRef } from 'react'
import Sidebar from './components/Sidebar'
import Topbar from './components/Topbar'
import Dashboard from './pages/Dashboard'
import AnalysisReport from './pages/AnalysisReport'
import DataCenter from './pages/DataCenter'
import Toast from './components/Toast'
import { uploadVideo, fetchReport, createProgressStream } from './api'

const SIDEBAR_VIEW = { DASHBOARD: 'dashboard', ANALYSIS: 'analysis', DATA_CENTER: 'data_center' }
const DASHBOARD_STATE = { UPLOAD: 'upload', PROGRESS: 'progress' }

let toastIdCounter = 0

export default function App() {
  const [activeView,        setActiveView]      = useState(SIDEBAR_VIEW.DASHBOARD)
  const [dashboardState,    setDashboardState]  = useState(DASHBOARD_STATE.UPLOAD)
  
  const [jobId,             setJobId]           = useState(null)
  const [progress,          setProgress]        = useState({ percent: 0, message: '', logs: [] })
  const [report,            setReport]          = useState(null)
  const [toasts,            setToasts]          = useState([])
  const cleanupSseRef       = useRef(null)

  // ── Toast helpers ────────────────────────────────────────────────────────
  const addToast = (message, type = 'info') => {
    const id = ++toastIdCounter
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000)
  }

  // ── Upload + analysis flow ───────────────────────────────────────────────
  async function handleAnalyze(file, useVlm) {
    try {
      addToast('Uploading video…', 'info')
      setProgress({ percent: 0, message: 'Uploading video to server…', logs: [] })
      setDashboardState(DASHBOARD_STATE.PROGRESS)
      
      const { job_id } = await uploadVideo(file, useVlm, (percent) => {
        setProgress(prev => {
          const msg = `Uploading: ${percent}%`
          const lastLog = prev.logs[prev.logs.length - 1]
          return {
            percent,
            message: 'Uploading video to server…',
            logs: (lastLog && lastLog.startsWith('Uploading:')) 
              ? [...prev.logs.slice(0, -1), msg] 
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
      throw err
    }
  }

  function startStreaming(jobId) {
    if (cleanupSseRef.current) cleanupSseRef.current()

    const cleanup = createProgressStream(
      jobId,
      (data) => {
        const now = new Date().toLocaleTimeString()
        setProgress(prev => ({
          percent: data.percent ?? prev.percent,
          message: data.message ?? prev.message,
          logs: data.message
            ? [...prev.logs, `[${now}] ${data.message}`]
            : prev.logs,
        }))
      },
      () => {
        addToast('Analysis complete! Loading report…', 'success')
        loadReport(jobId)
      },
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
      setActiveView(SIDEBAR_VIEW.ANALYSIS)
      addToast('Report ready! 🎉', 'success')
    } catch (err) {
      addToast(`Could not load report: ${err.message}`, 'error')
      resetToUpload()
    }
  }

  async function pollForReport(jobId) {
    for (let i = 0; i < 60; i++) {
      await new Promise(r => setTimeout(r, 5000))
      try {
        const res = await fetch(`/api/report/${jobId}`)
        if (res.status === 200) {
          const data = await res.json()
          setReport(data)
          setActiveView(SIDEBAR_VIEW.ANALYSIS)
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
    setActiveView(SIDEBAR_VIEW.DASHBOARD)
    setDashboardState(DASHBOARD_STATE.UPLOAD)
    setJobId(null)
    setReport(null)
    setProgress({ percent: 0, message: '', logs: [] })
  }

  // ── Render ───────────────────────────────────────────────────────────────
  
  const getSubTitle = () => {
    if (activeView === SIDEBAR_VIEW.ANALYSIS) return `Session / ${jobId ? jobId.substring(0,8) : 'None'}`
    if (activeView === SIDEBAR_VIEW.DATA_CENTER) return "Global Inference Logs"
    return "Node Alpha Operational"
  }

  return (
    <div className="flex bg-background text-on-surface min-h-screen">
      <Sidebar activeView={activeView} setActiveView={setActiveView} />

      <main className="ml-64 flex-1 flex flex-col min-h-screen h-screen">
        <Topbar 
            title={
                activeView === SIDEBAR_VIEW.DASHBOARD ? "Live Stream & Inference" :
                activeView === SIDEBAR_VIEW.ANALYSIS ? "Semantic Engine Analysis" :
                "Historical Data Center"
            } 
            subtitle={getSubTitle()} 
        />
        
        <div className="flex-1 overflow-auto bg-surface-bright pb-10">
            {activeView === SIDEBAR_VIEW.DASHBOARD && (
                <Dashboard 
                    onAnalyze={handleAnalyze} 
                    view={dashboardState} 
                    progress={progress} 
                    jobId={jobId} 
                />
            )}

            {activeView === SIDEBAR_VIEW.ANALYSIS && report && (
                <AnalysisReport 
                    data={report} 
                    jobId={jobId} 
                    onReset={resetToUpload} 
                />
            )}

            {activeView === SIDEBAR_VIEW.ANALYSIS && !report && (
                <div className="flex items-center justify-center p-20 text-on-surface-variant font-bold text-center">
                    No active analysis session found.<br/>Please run a video from the Overview tab.
                </div>
            )}

            {activeView === SIDEBAR_VIEW.DATA_CENTER && (
                <DataCenter />
            )}
            
            {/* Fallback for decorative side tabs */}
            {(activeView === 'reports' || activeView === 'settings') && (
                <div className="flex items-center justify-center p-20 text-outline-variant text-lg font-bold">
                    This section is part of the UI prototype and currently has no backend data bindings. Let's stick strictly to the functional tabs!
                </div>
            )}
        </div>
      </main>

      <Toast toasts={toasts} />
    </div>
  )
}
