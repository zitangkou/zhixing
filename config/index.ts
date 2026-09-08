import { defineConfig, type UserConfigExport } from '@tarojs/cli'
import path from 'path'
import devConfig from './dev'
import prodConfig from './prod'

export default defineConfig<'vite'>(async (merge) => {
  const baseConfig: UserConfigExport<'vite'> = {
    projectName: 'zhixing-gongkao',
    date: '2026-6-29',
    designWidth: 375,
    deviceRatio: {
      640: 2.34 / 2,
      750: 1,
      375: 2,
      828: 1.81 / 2,
    },
    sourceRoot: 'src',
    outputRoot: 'dist',
    plugins: [],
    defineConstants: {
      USE_MOCK: JSON.stringify(process.env.USE_MOCK === 'true'),
      // 空字符串表示 Docker 同域 /api；仅 undefined 时用本地开发地址
      API_BASE_URL: JSON.stringify(process.env.TARO_APP_API_URL ?? 'http://127.0.0.1:8001'),
      // general（综合版）/ shenlun（申论）/ theory（政治理论）
      PRODUCT_KEY: JSON.stringify(process.env.TARO_APP_PRODUCT_KEY ?? 'general'),
    },
    copy: {
      // 兜底：确保 tab 图标进入产物（H5 生产路径为 /static/images/）
      patterns: [
        { from: 'src/assets/icons/', to: 'dist/static/images/' },
      ],
      options: {},
    },
    framework: 'vue3',
    compiler: 'vite',
    alias: {
      '@': path.resolve(__dirname, '..', 'src'),
    },
    mini: {
      postcss: {
        pxtransform: { enable: true, config: {} },
        cssModules: { enable: false },
      },
    },
    h5: {
      publicPath: '/',
      staticDirectory: 'static',
      esnextModules: ['@nutui/nutui-taro'],
      devServer: { port: 10087 },
      postcss: {
        autoprefixer: { enable: true },
        cssModules: { enable: false },
      },
    },
  }

  if (process.env.NODE_ENV === 'development') {
    return merge({}, baseConfig, devConfig)
  }
  return merge({}, baseConfig, prodConfig)
})
