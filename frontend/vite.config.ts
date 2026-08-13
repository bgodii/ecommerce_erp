import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Em dev, o front roda em :5173 e faz proxy de /api para o backend em :8010.
// Em produção, o Nginx serve o build e faz o proxy de /api para o container da API.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8010', changeOrigin: true },
    },
  },
})
