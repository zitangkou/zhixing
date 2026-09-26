import type { Plugin } from 'vite'

/**
 * Taro 4.0.9 的 vite 小程序分包把 Vue 打进 taro.js，却把 @babel/runtime
 * 打进 vendors.js。NutUI 等 vendors 在模块初始化时调用 taro.defineComponent，
 * 而 taro.js 又在导出 defineComponent 之前 require(vendors.js)，循环依赖下
 * defineComponent 仍是空值，微信开发者工具报 `e.defineComponent is not a function`。
 *
 * 与上游 https://github.com/NervJS/taro/pull/17541 相同：把 @babel 拆到独立的
 * babelHelpers chunk，让 taro chunk 不再依赖 vendors。
 *
 * KaTeX：小程序端不再打包（src/utils/latex.weapp.ts 替代 latex.ts，公式显示纯文本），
 * 因此这里不再需要 KaTeX 分包与字体裁剪逻辑。
 */
const BABEL_DEP = /node_modules[\\/]@babel[\\/]/

export function weappBreakVueChunkCycle(): Plugin {
  return {
    name: 'weapp-break-vue-chunk-cycle',
    apply: 'build',
    enforce: 'post',
    config(viteConfig) {
      if (process.env.TARO_ENV !== 'weapp') return
      const output = viteConfig.build?.rollupOptions?.output
      if (!output || Array.isArray(output) || typeof output.manualChunks !== 'function') return
      const original = output.manualChunks
      output.manualChunks = (id, meta) => {
        if (BABEL_DEP.test(id)) return 'babelHelpers'
        return original(id, meta)
      }
    },
  }
}
