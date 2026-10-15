/** 1.3.4 的包含 d.ts 但未在 package.json 暴露 types；补齐当前调用的公开签名。 */
declare module '@rojer/katex-mini' {
  interface RichNode {
    type?: string
    name?: string
    text?: string
    attrs?: Record<string, string>
    children?: RichNode[]
  }
  interface ParseOptions {
    displayMode?: boolean
    throwError?: boolean
    throwOnError?: boolean
    strict?: string
    trust?: boolean
    maxExpand?: number
    maxSize?: number
  }
  export default function parse(latex: string, options?: ParseOptions): RichNode[]
}
