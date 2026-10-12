import katex from 'katex'
import type { KnowledgeBlock, StructuredNode, StructuredTree } from '@/api/knowledge'

function escapeHtml(value: string): string {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;')
}

function imageUrl(value: string): string {
  const url = value.trim()
  if (/^https:\/\//i.test(url)) return url
  if (/^\/uploads\/knowledge-media\/[a-f0-9]{32}\.(png|jpg)$/i.test(url)) return new URL(url, window.location.origin).href
  return ''
}

function markdownBlock(block: KnowledgeBlock): string {
  if (block.type === 'text') return block.text.trim()
  if (block.type === 'formula') {
    return [`公式：${block.plain || block.latex}`, '```latex', block.latex, '```'].join('\n')
  }
  if (block.type === 'image') return imageUrl(block.url) ? `![${block.alt || '知识框架配图'}](${imageUrl(block.url)})` : `图片：${block.alt || '资源地址不可用'}`
  return [`**例题**`, block.question.trim(), block.answer?.trim() ? `**解析**\n${block.answer.trim()}` : ''].filter(Boolean).join('\n\n')
}

export function knowledgeTreeToMarkdown(tree: StructuredTree): string {
  const lines = [`# ${tree.title.trim()}`]
  if (tree.description.trim()) lines.push('', tree.description.trim())
  const visit = (nodes: StructuredNode[], depth: number) => {
    for (const node of nodes) {
      lines.push('')
      if (depth <= 5) lines.push(`${'#'.repeat(depth + 2)} ${node.title.trim()}`)
      else lines.push(`${'  '.repeat(depth - 5)}- **${node.title.trim()}**`)
      for (const block of node.blocks) {
        const content = markdownBlock(block)
        if (content) lines.push('', content)
      }
      visit(node.children, depth + 1)
    }
  }
  visit(tree.children, 0)
  return `${lines.join('\n').trim()}\n`
}

function formulaHtml(latex: string, plain: string): string {
  try {
    return `<div class="formula">${katex.renderToString(latex, { output: 'mathml', throwOnError: false })}<small>${escapeHtml(plain)}</small></div>`
  } catch {
    return `<pre class="formula-source">${escapeHtml(plain || latex)}</pre>`
  }
}

function blockHtml(block: KnowledgeBlock): string {
  if (block.type === 'text') return `<div class="block text">${escapeHtml(block.text).replace(/\n/g, '<br>')}</div>`
  if (block.type === 'formula') return block.latex.trim() ? formulaHtml(block.latex, block.plain) : ''
  if (block.type === 'image') {
    const src = imageUrl(block.url)
    return src ? `<figure class="block"><img src="${escapeHtml(src)}" alt="${escapeHtml(block.alt || '')}">${block.alt ? `<figcaption>${escapeHtml(block.alt)}</figcaption>` : ''}</figure>` : `<p class="muted">图片资源地址无法导出</p>`
  }
  return `<section class="block example"><strong>例题</strong><p>${escapeHtml(block.question).replace(/\n/g, '<br>')}</p>${block.answer?.trim() ? `<strong>解析</strong><p>${escapeHtml(block.answer).replace(/\n/g, '<br>')}</p>` : ''}</section>`
}

export function knowledgeTreeToHtml(tree: StructuredTree, exportedAt = new Date()): string {
  const toc: string[] = []
  let sequence = 0
  const renderNodes = (nodes: StructuredNode[], depth: number): string => nodes.map((node) => {
    const id = `section-${++sequence}`
    toc.push(`<li class="toc-depth-${Math.min(depth, 5)}"><a href="#${id}">${escapeHtml(node.title)}</a></li>`)
    const level = Math.min(depth + 2, 6)
    const blocks = node.blocks.map(blockHtml).filter(Boolean).join('\n')
    return `<section class="node depth-${Math.min(depth, 5)}"><h${level} id="${id}">${escapeHtml(node.title)}</h${level}>${blocks}${renderNodes(node.children, depth + 1)}</section>`
  }).join('\n')
  const body = renderNodes(tree.children, 0)
  const tocHtml = toc.length ? `<nav class="toc"><h2>目录</h2><ol>${toc.join('')}</ol></nav>` : ''
  return `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(tree.title)}｜知识框架</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f5f6f8;color:#202124;font:16px/1.8 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}.page{max-width:960px;margin:32px auto;padding:48px 64px;background:#fff;box-shadow:0 4px 24px #0000000d}header{border-bottom:3px solid #d0021b;padding-bottom:20px;margin-bottom:28px}h1{font-size:32px;line-height:1.3;margin:0 0 8px;color:#38271d}header p,.meta,.muted,figcaption{color:#697078}.meta{font-size:13px}.toc{background:#faf7f3;border-radius:8px;padding:16px 24px;margin:24px 0}.toc h2{font-size:18px;margin:0 0 8px}.toc ol{margin:0;padding-left:22px}.toc-depth-1{margin-left:16px}.toc-depth-2{margin-left:32px}.toc-depth-3,.toc-depth-4,.toc-depth-5{margin-left:48px}.node{margin:18px 0}.node h2,.node h3,.node h4,.node h5,.node h6{color:#34271f;line-height:1.45;margin:20px 0 8px}.node h2{font-size:24px;border-left:4px solid #d0021b;padding-left:12px}.node h3{font-size:21px}.node h4{font-size:19px}.node h5,.node h6{font-size:17px}.block{margin:12px 0;padding:14px 18px;background:#fafafa;border-radius:8px;overflow-wrap:anywhere}.example{border-left:3px solid #d0021b}.example strong{color:#9b0d1b}.formula{overflow-x:auto;padding:8px}.formula small{display:block;color:#697078;margin-top:6px}img{max-width:100%;height:auto}figure{margin:12px 0}figcaption{font-size:13px}.text{white-space:normal}footer{margin-top:40px;border-top:1px solid #e7e2dc;padding-top:12px;color:#7b7b7b;font-size:12px}@media print{body{background:#fff}.page{margin:0;padding:16mm;max-width:none;box-shadow:none}.node{break-inside:avoid}a{color:inherit;text-decoration:none}}
</style></head><body><main class="page"><header><h1>${escapeHtml(tree.title)}</h1>${tree.description.trim() ? `<p>${escapeHtml(tree.description)}</p>` : ''}<div class="meta">知识框架 · 导出于 ${escapeHtml(exportedAt.toLocaleString('zh-CN'))}</div></header>${tocHtml}<article>${body}</article><footer>由知行知识框架工作台导出</footer></main></body></html>`
}

export function downloadKnowledgeFile(filename: string, content: string | Blob, mime: string): void {
  const url = URL.createObjectURL(new Blob([content], { type: mime }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
