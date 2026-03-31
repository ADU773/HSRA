import styles from './VlmDescriptions.module.css'

export default function VlmDescriptions({ descriptions }) {
  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <h3 className={styles.cardTitle}>🔬 VLM Scene Descriptions</h3>
        <span className={`${styles.badge} ${styles.badgeBlue}`}>{descriptions.length}</span>
      </div>
      <div className={styles.body}>
        {descriptions.length === 0 ? (
          <div className={styles.empty}>VLM descriptions not available or disabled.</div>
        ) : descriptions.map((vd, i) => (
          <div key={i} className={styles.item}>
            <div className={styles.time}>🔍 {vd.time_formatted}</div>
            <div className={styles.desc}>{vd.description}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
