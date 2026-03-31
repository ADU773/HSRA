import { useEffect, useRef } from 'react'
import styles from './ProgressSection.module.css'

export default function ProgressSection({ progress }) {
  const logRef = useRef()

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [progress.logs])

  const pct = progress.percent ?? 0

  return (
    <section className={styles.section} id="progress">
      <div className="container">
        <div className={styles.card}>
          <div className={styles.header}>
            <div className={styles.spinner} />
            <div className={styles.info}>
              <h3 className={styles.title}>
                {progress.message && progress.message.includes('Uploading') ? 'Uploading Video…' : 'Analysing Video…'}
              </h3>
              <p className={styles.msg}>{progress.message || 'Initialising…'}</p>
            </div>
            <span className={styles.pct}>{Math.round(pct)}%</span>
          </div>

          <div className={styles.barWrap}>
            <div className={styles.bar} style={{ width: `${pct}%` }} />
          </div>

          <div className={styles.log} ref={logRef}>
            {progress.logs?.map((log, i) => (
              <div key={i} className={`${styles.logEntry} ${i === progress.logs.length - 1 ? styles.logLast : ''}`}>
                {log}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
