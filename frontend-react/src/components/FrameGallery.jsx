import { useState, useEffect } from 'react'
import { fetchFrameList, frameUrl } from '../api'
import styles from './FrameGallery.module.css'

export default function FrameGallery({ jobId }) {
  const [frames, setFrames]   = useState([])
  const [idx, setIdx]         = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchFrameList(jobId)
      .then(d => { setFrames(d.frames || []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [jobId])

  const prev = () => setIdx(i => (i - 1 + frames.length) % frames.length)
  const next = () => setIdx(i => (i + 1) % frames.length)

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <h3 className={styles.cardTitle}>🖼 Annotated Frame Gallery</h3>
        <div className={styles.controls}>
          <button className={styles.navBtn} onClick={prev} disabled={!frames.length}>‹</button>
          <span className={styles.counter}>{frames.length ? `${idx + 1} / ${frames.length}` : '—'}</span>
          <button className={styles.navBtn} onClick={next} disabled={!frames.length}>›</button>
        </div>
      </div>

      <div className={styles.mainWrap}>
        {loading && <div className={styles.placeholder}>Loading frames…</div>}
        {!loading && !frames.length && <div className={styles.placeholder}>No annotated frames.</div>}
        {!loading && frames.length > 0 && (
          <img
            key={frames[idx]}
            src={frameUrl(jobId, frames[idx])}
            alt={`Frame ${frames[idx]}`}
            className={styles.mainImg}
          />
        )}
      </div>

      {frames.length > 0 && (
        <div className={styles.thumbsWrap}>
          {frames.slice(0, 12).map((fi, ti) => (
            <div
              key={fi}
              className={`${styles.thumb} ${ti === idx ? styles.thumbActive : ''}`}
              onClick={() => setIdx(ti)}
            >
              <img src={frameUrl(jobId, fi)} alt="" loading="lazy" />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
