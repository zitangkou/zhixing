import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8001'

export default defineConfig({
  plugins: [vue()],
  base: '/manage/',
  resolve: {
    alias: { '@': resolve(__dirname, 'src') },
    extensions: ['.ts', '.tsx', '.vue', '.js', '.json'],
  },
  server: {
    port: 5173,
    proxy: {
      '/admin': apiProxyTarget,
      '/api': apiProxyTarget,
      '/uploads': apiProxyTarget,
    },
  },
  build: {
    outDir: '../admin-dist',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vue: ['vue', 'vue-router', 'pinia'],
          element: ['element-plus', '@element-plus/icons-vue'],
          katex: ['katex'],
        },
      },
    },
  },
})
