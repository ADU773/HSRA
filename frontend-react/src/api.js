// src/api.js — All API calls to Flask backend
const BASE = '/api'

export function uploadVideo(file, useVlm, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${BASE}/upload`)

    if (onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          onProgress(Math.round((e.loaded / e.total) * 100))
        }
      }
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText))
      } else {
        try {
          const err = JSON.parse(xhr.responseText)
          reject(new Error(err.error || 'Upload failed'))
        } catch {
          reject(new Error('Upload failed'))
        }
      }
    }
    xhr.onerror = () => reject(new Error('Network error during upload'))

    const form = new FormData()
    form.append('video', file)
    form.append('use_vlm', useVlm ? 'true' : 'false')
    xhr.send(form)
  })
}

export async function fetchReport(jobId) {
  const res = await fetch(`${BASE}/report/${jobId}`)
  if (!res.ok) throw new Error('Report not ready')
  return res.json()
}

export async function fetchFrameList(jobId) {
  const res = await fetch(`${BASE}/frames/${jobId}`)
  return res.json() // { frames: [...] }
}

export function frameUrl(jobId, frameIdx) {
  return `${BASE}/frame/${jobId}/${frameIdx}`
}

export function csvUrl(jobId) {
  return `${BASE}/download/csv/${jobId}`
}

export async function checkVlm() {
  try {
    const res = await fetch(`${BASE}/vlmcheck`)
    if (!res.ok) return { vlm_available: false }
    return await res.json()
  } catch { return { vlm_available: false } }
}

export function createProgressStream(jobId, onMessage, onDone, onError) {
  const es = new EventSource(`${BASE}/status/${jobId}`)
  es.onmessage = (e) => {
    const data = JSON.parse(e.data)
    onMessage(data)
    if (data.status === 'done') { es.close(); onDone() }
    if (data.status === 'error') { es.close(); onError(data.error || 'Unknown error') }
  }
  es.onerror = () => {
    es.close()
    onError('Connection lost — polling…')
  }
  return () => es.close() // cleanup fn
}
