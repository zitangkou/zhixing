import type { UserConfigExport } from '@tarojs/cli'

export default {
  mini: {
    // 生产 weapp JS 压缩（质量审计「JS 未压缩」）
    terser: {
      enable: true,
      config: {
        compress: true,
        mangle: true,
      },
    },
  },
  h5: { legacy: false },
} satisfies UserConfigExport<'vite'>
