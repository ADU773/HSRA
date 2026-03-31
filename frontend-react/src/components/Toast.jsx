import { useEffect } from 'react'
import styles from './Toast.module.css'

const ICONS = { success: '✅', error: '❌', warn: '⚠️', info: 'ℹ️' }

export default function Toast({ toasts }) {
  return (
    <div className={styles.container}>
      {toasts.map(t => (
        <ToastItem key={t.id} toast={t} />
      ))}
    </div>
  )
}

function ToastItem({ toast }) {
  return (
    <div className={`${styles.toast} ${styles[toast.type] || ''}`}>
      <span className={styles.icon}>{ICONS[toast.type] || 'ℹ️'}</span>
      <span className={styles.msg}>{toast.message}</span>
    </div>
  )
}
