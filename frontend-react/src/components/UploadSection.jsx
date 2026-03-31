import { useRef, useState } from 'react'
import { fmtBytes } from '../utils'
import styles from './UploadSection.module.css'

export default function UploadSection({ onAnalyze }) {
  const [file, setFile] = useState(null)
  const [useVlm, setUseVlm] = useState(true)
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const inputRef = useRef()

  const ALLOWED_EXT = ['mp4','avi','mov','mkv','webm','m4v']

  function handleFile(f) {
    const ext = f.name.split('.').pop().toLowerCase()
    if (!ALLOWED_EXT.includes(ext)) {
      alert(`Unsupported file type: .${ext}\nUse MP4, AVI, MOV, MKV or WebM.`)
      return
    }
    setFile(f)
  }

  function onDrop(e) {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }

  async function handleAnalyze() {
    if (!file || uploading) return
    setUploading(true)
    try { await onAnalyze(file, useVlm) }
    catch { setUploading(false) }
  }

  return (
    <section className={styles.section} id="upload">
      <div className="container">
        <div className={styles.header}>
          <h2 className={styles.title}>Upload Video</h2>
          <p className={styles.sub}>Supports MP4, AVI, MOV, MKV, WebM · Up to 2 GB</p>
        </div>

        {/* VLM toggle */}
        <div className={styles.optionsRow}>
          <label className={styles.toggleLabel}>
            <input type="checkbox" checked={useVlm} onChange={e => setUseVlm(e.target.checked)} hidden />
            <span className={styles.toggleTrack}>
              <span className={`${styles.toggleThumb} ${useVlm ? styles.thumbOn : ''}`} />
            </span>
            <span className={styles.toggleText}>Enable VLM Scene Descriptions</span>
            <span className={styles.toggleHint}>(nanoVLM — adds ~2s per scene sample)</span>
          </label>
        </div>

        {/* Drop zone */}
        {!file && (
          <div
            className={`${styles.dropZone} ${dragOver ? styles.dragOver : ''}`}
            onClick={() => inputRef.current.click()}
            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            role="button"
            tabIndex={0}
            onKeyDown={e => e.key === 'Enter' && inputRef.current.click()}
          >
            <input
              ref={inputRef}
              type="file"
              accept="video/*"
              hidden
              onChange={e => e.target.files[0] && handleFile(e.target.files[0])}
            />
            <div className={styles.iconWrap}><span className={styles.icon}>📹</span></div>
            <p className={styles.dzTitle}>Drag &amp; drop your video here</p>
            <p className={styles.dzSub}>or</p>
            <button className={styles.browseBtn} onClick={e => { e.stopPropagation(); inputRef.current.click() }}>
              Browse file
            </button>
            <p className={styles.formats}>MP4 · AVI · MOV · MKV · WebM</p>
          </div>
        )}

        {/* File preview */}
        {file && (
          <div className={styles.preview}>
            <span className={styles.previewIcon}>🎬</span>
            <div className={styles.previewInfo}>
              <span className={styles.previewName}>{file.name}</span>
              <span className={styles.previewSize}>{fmtBytes(file.size)}</span>
            </div>
            <button
              className={styles.analyzeBtn}
              onClick={handleAnalyze}
              disabled={uploading}
            >
              {uploading ? 'Uploading…' : 'Start Analysis'}
              {!uploading && (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M5 3l14 9-14 9V3z"/>
                </svg>
              )}
            </button>
            <button className={styles.clearBtn} onClick={() => setFile(null)} title="Remove file">✕</button>
          </div>
        )}
      </div>
    </section>
  )
}
