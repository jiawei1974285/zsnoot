import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// 单体模式（默认，兼容旧部署）：Vite proxy /api → 本机 127.0.0.1:5004
// 分离模式：在 .env 里配置 VITE_CLOUD_API / VITE_LOCAL_API；前端经 apiClient.js 自行寻址
//          分离模式下 Vite proxy 不再需要（fetch 用绝对 URL），但留着也无害
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const cloudApi = env.VITE_CLOUD_API
  return {
    plugins: [vue()],
    server: cloudApi
      ? {}                        // 分离模式：让浏览器直接 CORS 跨域
      : { proxy: { '/api': 'http://127.0.0.1:5004' } },
    build: {
      outDir: 'dist',
      emptyOutDir: true,
      chunkSizeWarningLimit: 1400,
    },
  }
})
