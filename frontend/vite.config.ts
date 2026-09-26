import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// В разработке /api проксируется на бэкенд - фронтенд и API на одном origin, поэтому cookie
// сессии Я ID работает без CORS. В продакшене то же самое делает nginx (см. frontend/nginx.conf).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': { target: env.VITE_API_PROXY ?? 'http://localhost:8000', changeOrigin: false },
      },
    },
  }
})
