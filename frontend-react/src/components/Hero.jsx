import styles from './Hero.module.css'

export default function Hero() {
  return (
    <section className={styles.hero}>
      <div className={styles.bgCircles} aria-hidden>
        <div className={`${styles.circle} ${styles.c1}`} />
        <div className={`${styles.circle} ${styles.c2}`} />
        <div className={`${styles.circle} ${styles.c3}`} />
      </div>

      <div className={styles.content}>
        <div className={styles.badge}>🤖 Dual-YOLO · BoT-SORT · nanoVLM</div>
        <h1 className={styles.title}>
          Intelligent Trash<br/>Detection Analytics
        </h1>
        <p className={styles.subtitle}>
          Upload a surveillance video. Our AI detects persons, vehicles &amp; trash,
          tracks every object with persistent IDs, flags littering events with
          precise timestamps, and generates a full semantic report.
        </p>
        <a href="#upload" className={styles.cta}>
          <span>Analyse a Video</span>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M5 12h14M12 5l7 7-7 7"/>
          </svg>
        </a>
      </div>

      <div className={styles.pills}>
        {['👤 Person Tracking','🚗 Vehicle Detection','🗑 Trash Detection','📋 Incident Reports','🔬 VLM Scene Description'].map((p, i) => (
          <div key={i} className={styles.pill} style={{ animationDelay: `${i * 0.07}s` }}>{p}</div>
        ))}
      </div>
    </section>
  )
}
