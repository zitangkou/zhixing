import { defineConfig, type UserConfigExport } from '@tarojs/cli'
import path from 'node:path'

export default defineConfig<'vite'>(async () => {
  const config: UserConfigExport<'vite'> = {
    projectName: 'ai-toolbox',
    date: '2026-10-08',
    designWidth: 375,
    deviceRatio: { 640: 2.34 / 2, 750: 1, 375: 2, 828: 1.81 / 2 },
    sourceRoot: 'src',
    outputRoot: 'dist',
    plugins: [],
    defineConstants: {
      API_BASE_URL: JSON.stringify(process.env.TARO_APP_API_BASE_URL ?? ''),
      APP_ENV: JSON.stringify(process.env.TARO_APP_ENV ?? process.env.NODE_ENV ?? 'development'),
    },
    framework: 'vue3',
    compiler: { type: 'vite' },
    alias: { '@': path.resolve(__dirname, '../src') },
    mini: { postcss: { pxtransform: { enable: true, config: {} }, cssModules: { enable: false } } },
    h5: { publicPath: '/', staticDirectory: 'static', devServer: { port: 10088 } },
  }
  return config
})
