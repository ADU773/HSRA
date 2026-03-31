import { fmtDuration } from '../utils'
import styles from './StatGrid.module.css'

const CARDS = [
  { id: 'duration',  icon: '⏱',  label: 'Duration',          key: d => fmtDuration(d.duration_sec) },
  { id: 'persons',   icon: '👤',  label: 'Persons Tracked',   key: d => d.unique_persons },
  { id: 'cars',      icon: '🚗',  label: 'Vehicles Tracked',  key: d => d.unique_cars },
  { id: 'trash',     icon: '🗑',  label: 'Trash Items',       key: d => d.unique_trash },
  { id: 'events',    icon: '⚠️',  label: 'Littering Events',  key: d => d.total_events, alert: true },
  { id: 'fps',       icon: '🎞',  label: 'Video FPS',         key: d => d.fps },
]

export default function StatGrid({ data }) {
  return (
    <div className={styles.grid}>
      {CARDS.map((c, i) => (
        <div
          key={c.id}
          className={`${styles.card} ${c.alert ? styles.alert : ''}`}
          style={{ animationDelay: `${i * 0.07}s` }}
        >
          <div className={styles.icon}>{c.icon}</div>
          <div className={`${styles.val} ${c.alert ? styles.alertVal : ''}`}>{c.key(data)}</div>
          <div className={styles.label}>{c.label}</div>
        </div>
      ))}
    </div>
  )
}
