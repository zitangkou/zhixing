import { defineConfig } from '@tarojs/cli'
import path from 'path'

export default defineConfig((merge) => merge({}, {
  projectName: '言遇英语',
  date: '2026-10-10',
  designWidth: 750,
  deviceRatio: { 750: 1 },
  sourceRoot: 'src',
  outputRoot: 'dist',
  plugins: [],
  framework: 'vue3',
  compiler: { type: 'vite', vitePlugins: [] },
  alias: { '@': path.resolve(__dirname, '..', 'src') },
  mini: { postcss: { pxtransform: { enable: true, config: {} }, url: { enable: true, config: { limit: 1024 } } } },
  h5: { publicPath: '/', staticDirectory: 'static', postcss: { autoprefixer: { enable: true, config: {} } } },
}))
