import type { Plugin } from 'vite'

/** 多个分包共享公式引擎，固定放在主包；禁止主包反向 require 某个业务分包。 */
export function weappMathChunk(): Plugin {
  return {
    name: 'weapp-math-chunk',
    apply: () => process.env.TARO_ENV === 'weapp',
    outputOptions(options) {
      const previous = options.manualChunks
      if (typeof previous === 'object' && previous !== null) return null
      return {
        ...options,
        manualChunks(id, meta) {
          if (/node_modules[\\/]katex[\\/]/.test(id)) return 'katex'
          return typeof previous === 'function' ? previous(id, meta) : undefined
        },
      }
    },
  }
}
