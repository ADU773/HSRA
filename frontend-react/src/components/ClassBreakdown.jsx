import { useEffect, useRef } from 'react'
import styles from './ClassBreakdown.module.css'

const COLOR = {
  person: '#10b981', car: '#3b82f6', truck: '#3b82f6',
  bus: '#3b82f6', bicycle: '#8b5cf6', motorcycle: '#8b5cf6',
}

export default function ClassBreakdown({ counts }) {
  const entries = Object.entries(counts || {}).sort((a, b) => b[1] - a[1])
  const max = entries[0]?.[1] || 1

  const fillRefs = useRef([])

  useEffect(() => {
    // Animate bars after mount
    const timers = fillRefs.current.map((el, i) => {
      if (!el) return null
      const pct = Math.round((entries[i][1] / max) * 100)
      const t = setTimeout(() => { el.style.width = pct + '%' }, 80)
      return t
    })
    return () => timers.forEach(t => t && clearTimeout(t))
  }, [counts])

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <h3 className={styles.cardTitle}>📊 Detection Breakdown</h3>
      </div>
      <div className={styles.body}>
        {entries.length === 0
          ? <div className={styles.empty}>No detections.</div>
          : entries.map(([cls, cnt], i) => (
            <div key={cls} className={styles.row}>
              <div className={styles.labelRow}>
                <span className={styles.name}>{cls}</span>
                <span className={styles.cnt}>{cnt.toLocaleString()}</span>
              </div>
              <div className={styles.track}>
                <div
                  ref={el => fillRefs.current[i] = el}
                  className={styles.fill}
                  style={{ background: COLOR[cls] || '#ef4444', width: '0%' }}
                />
              </div>
            </div>
          ))
        }
      </div>
    </div>
  )
}
