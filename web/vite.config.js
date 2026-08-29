import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backend = (env.VITE_API_BASE_URL || env.BACKEND_URL || 'http://localhost:8000').replace(/\/$/, '')

  return {
    plugins: [react(), tailwindcss()],
    server: {
      // 项目路径含冒号("Beyond Prompt:")导致 fs.allow 误判 index.html 在白名单外,关闭严格检查
      fs: { strict: false },
      // 允许 Cloudflare Tunnel / localtunnel 等临时公网域名访问本地 Vite dev server
      allowedHosts: true,
      proxy: {
        '/api': backend,
        '/static': backend,
      },
    },
    preview: {
      proxy: {
        '/api': backend,
        '/static': backend,
      },
    },
  }
})
