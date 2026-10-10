import { defineConfig, type UserConfigExport } from '@tarojs/cli'
import path from 'node:path'

export default defineConfig<'vite'>(async () => {
  const config: UserConfigExport<'vite'> = {
    projectName: 'guangxian-lianxibu', date: '2026-10-10', designWidth: 375,
    deviceRatio: { 375: 2, 750: 1 }, sourceRoot: 'src', outputRoot: 'dist', framework: 'vue3',
    compiler: { type: 'vite' }, alias: { '@': path.resolve(__dirname, '../src') },
    mini: { postcss: { pxtransform: { enable: true, config: {} }, cssModules: { enable: false } } },
    h5: { publicPath: '/', staticDirectory: 'static', devServer: { port: 10090 }, postcss: { autoprefixer: { enable: true }, cssModules: { enable: false } } },
  }
  return config
})
