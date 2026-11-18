import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'node:fs'
import path from 'node:path'

// В dev-режиме запросы /api проксируются на бэкенд (по умолчанию порт 8000,
// можно переопределить через VITE_PROXY_TARGET).
// В production статику раздаёт nginx, который сам проксирует /api на backend-контейнер.
const proxyTarget = process.env.VITE_PROXY_TARGET || 'http://localhost:8000'

// HTTPS в dev-режиме: включается автоматически, если в ./certs лежат
// localhost.pem и localhost.key (генерация: см. README, раздел HTTPS).
const keyFile = path.resolve('certs/localhost.key')
const certFile = path.resolve('certs/localhost.pem')
const https =
  fs.existsSync(keyFile) && fs.existsSync(certFile)
    ? { key: fs.readFileSync(keyFile), cert: fs.readFileSync(certFile) }
    : undefined

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    ...(https ? { https } : {}),
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})
