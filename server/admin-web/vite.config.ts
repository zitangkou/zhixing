import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

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
      '/admin': 'http://127.0.0.1:8001',
      '/api': 'http://127.0.0.1:8001',
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
