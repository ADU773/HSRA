import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        timeout: 0,           // no proxy-level timeout (let Flask handle it)
        proxyTimeout: 0,      // no read timeout for large uploads / long analysis
      },
    },
  },
})
