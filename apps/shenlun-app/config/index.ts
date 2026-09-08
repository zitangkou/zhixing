import { defineConfig, type UserConfigExport } from '@tarojs/cli'
import path from 'path'

export default defineConfig<'vite'>(() => ({
  projectName: 'zhixing-shenlun',
  date: '2026-08-23',
  designWidth: 375,
  deviceRatio: { 375: 2, 640: 2.34 / 2, 750: 1, 828: 1.81 / 2 },
  sourceRoot: 'src',
  outputRoot: 'dist',
  framework: 'vue3',
  compiler: 'vite',
  alias: { '@': path.resolve(__dirname, '..', 'src') },
  defineConstants: {
    API_BASE_URL: JSON.stringify(process.env.TARO_APP_API_URL ?? 'http://127.0.0.1:8001'),
    APP_PUBLIC_PATH: JSON.stringify(process.env.TARO_APP_PUBLIC_PATH ?? '/'),
    PRODUCT_KEY: JSON.stringify('shenlun'),
    USE_MOCK: JSON.stringify(process.env.USE_MOCK === 'true'),
  },
  mini: { postcss: { pxtransform: { enable: true, config: {} }, cssModules: { enable: false } } },
  h5: {
    publicPath: process.env.TARO_APP_PUBLIC_PATH ?? '/',
    staticDirectory: 'static',
    devServer: { port: 10088 },
    postcss: { autoprefixer: { enable: true }, cssModules: { enable: false } },
  },
}) satisfies UserConfigExport<'vite'>)
