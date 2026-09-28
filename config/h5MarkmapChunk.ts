import type { Plugin } from 'vite'

/**
 * H5：MarkmapView.h5.vue 用 `await import('markmap-view')` 按需加载导图，
 * 但 Taro vite-runner 的 manualChunks 会把所有 node_modules 并进 vendors.js，
 * 首屏白白多下载约 400KB（markmap + d3）。这里包一层 manualChunks，
 * 把 markmap* / d3* 单独拆成 markmap chunk，仅打开知识导图时加载。
 * 小程序端不走 markmap（MarkmapView.weapp.vue 用分片图），插件在非 h5 下不生效。
 */
const MARKMAP_DEP = /node_modules[\\/](markmap-[^\\/]+|d3(-[^\\/]+)?)[\\/]/

export function h5MarkmapChunk(): Plugin {
  return {
    name: 'h5-markmap-chunk',
    apply: () => process.env.TARO_ENV === 'h5',
    outputOptions(opts) {
      const prev = opts.manualChunks
      if (typeof prev === 'object' && prev !== null) return null
      return {
        ...opts,
        manualChunks(id, meta) {
          if (MARKMAP_DEP.test(id)) return 'markmap'
          return typeof prev === 'function' ? prev(id, meta) : undefined
        },
      }
    },
  }
}
