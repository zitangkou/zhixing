import type { Plugin } from 'vite'

/** Keep the KaTeX parser in the shared main package: LatexBlock is used across subpackages. */
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
