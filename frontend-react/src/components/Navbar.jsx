import styles from './Navbar.module.css'

export default function Navbar({ showResults, vlmAvailable }) {
  return (
    <nav className={styles.navbar}>
      <div className={styles.inner}>
        <div className={styles.logo}>
          <span className={styles.logoIcon}>🗑️</span>
          <span className={styles.logoText}>TrashGuard</span>
        </div>
        <div className={styles.links}>
          <a href="#upload" className={styles.link}>Upload</a>
          {showResults && <a href="#results" className={styles.link}>Results</a>}
          <span className={`${styles.badge} ${vlmAvailable ? styles.badgeGreen : styles.badgeWarn}`}>
            {vlmAvailable ? '🟢 VLM Active' : '🟡 VLM Offline'}
          </span>
        </div>
      </div>
    </nav>
  )
}
