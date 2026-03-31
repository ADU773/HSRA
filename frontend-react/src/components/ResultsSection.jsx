import { csvUrl } from '../api'
import { fmtDuration } from '../utils'
import StatGrid from './StatGrid'
import EventsList from './EventsList'
import VlmDescriptions from './VlmDescriptions'
import FrameGallery from './FrameGallery'
import ClassBreakdown from './ClassBreakdown'
import TracksTable from './TracksTable'
import styles from './ResultsSection.module.css'

export default function ResultsSection({ data, jobId, onReset }) {

  function handlePrint() { window.print() }
  function handleCsv() {
    const a = document.createElement('a')
    a.href = csvUrl(jobId)
    a.download = `trash_report_${jobId.slice(0,8)}.csv`
    a.click()
  }

  return (
    <section className={styles.section} id="results">
      <div className="container">

        {/* Top bar */}
        <div className={styles.topBar}>
          <div>
            <h2 className={styles.title}>Analysis Report</h2>
            <p className={styles.meta}>
              Generated: {data.generated_at} · {data.width}×{data.height} · {data.fps} fps
            </p>
          </div>
          <div className={styles.actions}>
            <button className={styles.btnOutline} onClick={handleCsv}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/>
              </svg>
              Download CSV
            </button>
            <button className={styles.btnPrimary} onClick={handlePrint}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="6 9 6 2 18 2 18 9"/>
                <path d="M6 18H4a2 2 0 01-2-2v-5a2 2 0 012-2h16a2 2 0 012 2v5a2 2 0 01-2 2h-2"/>
                <rect x="6" y="14" width="12" height="8"/>
              </svg>
              Print Report
            </button>
            <button className={styles.btnSubtle} onClick={onReset}>New Analysis</button>
          </div>
        </div>

        <StatGrid data={data} />

        <div className={styles.grid}>
          <div className={styles.col}>
            <EventsList events={data.throwing_events || []} />
            <VlmDescriptions descriptions={data.vlm_descriptions || []} />
          </div>
          <div className={styles.col}>
            <FrameGallery jobId={jobId} />
            <ClassBreakdown counts={data.class_counts || {}} />
            <TracksTable tracks={data.track_timeline || []} />
          </div>
        </div>

        {/* Print-only summary */}
        <div className={`${styles.printReport} print-only`}>
          <h1>🗑️ TrashGuard — Incident Analysis Report</h1>
          <p>Generated: {data.generated_at}</p>
          <h2>Summary</h2>
          <p>Duration: {fmtDuration(data.duration_sec)} · Persons: {data.unique_persons} · Vehicles: {data.unique_cars} · Trash: {data.unique_trash} · Events: {data.total_events}</p>
          <h2>Littering Events</h2>
          {data.throwing_events?.length === 0
            ? <p>No events detected.</p>
            : data.throwing_events?.map((ev, i) => (
              <p key={i}><strong>#{i+1} [{ev.time_formatted}]</strong> — {ev.description}</p>
            ))
          }
          {data.vlm_descriptions?.length > 0 && <>
            <h2>VLM Scene Descriptions</h2>
            {data.vlm_descriptions.map((vd, i) => (
              <p key={i}><strong>[{vd.time_formatted}]</strong> {vd.description}</p>
            ))}
          </>}
        </div>

      </div>
    </section>
  )
}
