import styles from './EventsList.module.css'

export default function EventsList({ events }) {
  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <h3 className={styles.cardTitle}>⚠️ Littering / Throwing Events</h3>
        <span className={`${styles.badge} ${styles.badgeRed}`}>{events.length}</span>
      </div>
      <div className={styles.body}>
        {events.length === 0 ? (
          <div className={styles.empty}>✅ No littering events detected in this video.</div>
        ) : events.map((ev, i) => (
          <div key={i} className={styles.item}>
            <div className={styles.num}>{i + 1}</div>
            <div>
              <div className={styles.time}>⏱ {ev.time_formatted}</div>
              <div className={styles.desc}>{ev.description}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
