import styles from './TracksTable.module.css'

function badgeCls(cls) {
  if (cls === 'person') return styles.person
  if (['car','truck','bus','bicycle','motorcycle'].includes(cls)) return styles.vehicle
  return styles.trash
}

export default function TracksTable({ tracks }) {
  const sorted = [...(tracks || [])].sort((a, b) => a.class_name.localeCompare(b.class_name))
  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <h3 className={styles.cardTitle}>🏷 Object Track Summary</h3>
      </div>
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>ID</th><th>Class</th><th>Model</th>
              <th>First Seen</th><th>Last Seen</th><th>Detections</th>
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0
              ? <tr><td colSpan={6} className={styles.empty}>No tracks yet.</td></tr>
              : sorted.map((t, i) => (
                <tr key={i}>
                  <td><strong>#{t.track_id}</strong></td>
                  <td>
                    <span className={`${styles.badge} ${badgeCls(t.class_name)}`}>
                      {t.class_name}
                    </span>
                  </td>
                  <td>
                    <span className={`${styles.modelBadge} ${t.source_model === 'custom' ? styles.custom : styles.base}`}>
                      {t.source_model}
                    </span>
                  </td>
                  <td><code className={styles.code}>{t.first_seen_fmt}</code></td>
                  <td><code className={styles.code}>{t.last_seen_fmt}</code></td>
                  <td>{t.detections.toLocaleString()}</td>
                </tr>
              ))
            }
          </tbody>
        </table>
      </div>
    </div>
  )
}
