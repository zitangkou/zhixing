<template>
  <div class="project-manual-page">
    <el-card shadow="never" class="manual-cover">
      <div class="cover-eyebrow">ZHIXING · OPERATIONS GUIDE</div>
      <h1>操作指引</h1>
      <p>按产品、使用场景和操作流程查找说明，覆盖各小程序、H5、共享后端与管理后台。</p>
      <el-alert
        title="本文是全仓操作手册；知行公考的详细页面与路由清单仍以 FEATURES.md 为准。"
        type="info"
        :closable="false"
        show-icon
      />
    </el-card>

    <div class="manual-layout">
      <el-card shadow="never" class="manual-toc">
        <div class="toc-title">章节目录</div>
        <nav aria-label="操作指引章节目录">
          <a v-for="chapter in toc" :key="chapter.id" class="toc-link" :href="`#${chapter.id}`">{{ chapter.text }}</a>
        </nav>
        <div class="toc-footnote">点击章节可快速跳转</div>
      </el-card>

      <el-card shadow="never" class="manual-body">
        <template v-for="(block, index) in blocks" :key="index">
          <h1 v-if="block.type === 'heading' && block.level === 1 && index > 0" :id="block.id" class="appendix-title">{{ block.text }}</h1>
          <h2 v-else-if="block.type === 'heading' && block.level === 2" :id="block.id" class="chapter-title"><span class="chapter-mark"></span>{{ block.text }}</h2>
          <h3 v-else-if="block.type === 'heading'" :id="block.id" class="section-title">{{ block.text }}</h3>
          <p v-else-if="block.type === 'paragraph'">{{ block.text }}</p>
          <blockquote v-else-if="block.type === 'quote'">{{ block.text }}</blockquote>
          <pre v-else-if="block.type === 'code'"><code>{{ block.text }}</code></pre>
          <hr v-else-if="block.type === 'rule'" />
          <ul v-else-if="block.type === 'list' && !block.ordered">
            <li v-for="(item, itemIndex) in block.items" :key="itemIndex">{{ item }}</li>
          </ul>
          <ol v-else-if="block.type === 'list' && block.ordered">
            <li v-for="(item, itemIndex) in block.items" :key="itemIndex">{{ item }}</li>
          </ol>
          <div v-else-if="block.type === 'table'" class="table-wrap">
            <table>
              <thead><tr><th v-for="(cell, cellIndex) in block.headers" :key="cellIndex">{{ cell }}</th></tr></thead>
              <tbody>
                <tr v-for="(row, rowIndex) in block.rows" :key="rowIndex">
                  <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import manualSource from '../../../../../docs/PROJECT_OPERATIONS_MANUAL.md?raw'

type ManualBlock =
  | { type: 'heading'; level: number; text: string; id: string }
  | { type: 'paragraph' | 'quote' | 'code'; text: string }
  | { type: 'rule' }
  | { type: 'list'; ordered: boolean; items: string[] }
  | { type: 'table'; headers: string[]; rows: string[][] }

function cleanInline(value: string): string {
  return value
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1（$2）')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/__(.*?)__/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .trim()
}

function tableCells(line: string): string[] {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(cleanInline)
}

function isTableDivider(line: string): boolean {
  return line.includes('|') && /^\s*\|?\s*:?-{3,}/.test(line)
}

function parseManual(markdown: string): ManualBlock[] {
  const lines = markdown.split(/\r?\n/)
  const blocks: ManualBlock[] = []
  let index = 0
  let headingIndex = 0

  while (index < lines.length) {
    const line = lines[index].trim()
    if (!line) { index += 1; continue }

    if (line.startsWith('```')) {
      const code: string[] = []
      index += 1
      while (index < lines.length && !lines[index].trim().startsWith('```')) code.push(lines[index++])
      if (index < lines.length) index += 1
      blocks.push({ type: 'code', text: code.join('\n') })
      continue
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/)
    if (heading) {
      blocks.push({ type: 'heading', level: heading[1].length, text: cleanInline(heading[2]), id: `manual-section-${headingIndex++}` })
      index += 1
      continue
    }

    if (/^(---+|\*\*\*+|___+)$/.test(line)) {
      blocks.push({ type: 'rule' })
      index += 1
      continue
    }

    if (line.includes('|') && index + 1 < lines.length && isTableDivider(lines[index + 1])) {
      const headers = tableCells(line)
      index += 2
      const rows: string[][] = []
      while (index < lines.length && lines[index].trim().includes('|')) rows.push(tableCells(lines[index++]))
      blocks.push({ type: 'table', headers, rows })
      continue
    }

    if (/^[-*+]\s+/.test(line) || /^\d+\.\s+/.test(line)) {
      const ordered = /^\d+\.\s+/.test(line)
      const items: string[] = []
      while (index < lines.length) {
        const current = lines[index].trim()
        const match = current.match(ordered ? /^\d+\.\s+(.+)$/ : /^[-*+]\s+(.+)$/)
        if (!match) break
        items.push(cleanInline(match[1]))
        index += 1
      }
      blocks.push({ type: 'list', ordered, items })
      continue
    }

    if (line.startsWith('>')) {
      const quote: string[] = []
      while (index < lines.length && lines[index].trim().startsWith('>')) quote.push(cleanInline(lines[index++].trim().replace(/^>\s?/, '')))
      blocks.push({ type: 'quote', text: quote.join(' ') })
      continue
    }

    const paragraph: string[] = []
    while (index < lines.length && lines[index].trim() && !/^(#{1,3}\s|```|[-*+]\s|\d+\.\s|>)/.test(lines[index].trim())) {
      if (index + 1 < lines.length && lines[index].includes('|') && isTableDivider(lines[index + 1])) break
      paragraph.push(cleanInline(lines[index++].trim()))
    }
    if (paragraph.length) blocks.push({ type: 'paragraph', text: paragraph.join(' ') })
    else index += 1
  }

  return blocks
}

const blocks = computed(() => parseManual(manualSource))
const toc = computed(() => {
  return blocks.value.filter((block): block is Extract<ManualBlock, { type: 'heading' }> => block.type === 'heading' && block.level === 2)
})
</script>

<style scoped>
.project-manual-page { max-width: 1440px; margin: 0 auto; }
.manual-cover { margin-bottom: 18px; border: 0; border-radius: 16px; background: linear-gradient(125deg, var(--el-color-primary-light-9), var(--el-bg-color) 68%); }
.cover-eyebrow { color: var(--el-color-primary); font-size: 11px; font-weight: 700; letter-spacing: 1.7px; }
.manual-cover h1 { margin: 9px 0 7px; color: var(--el-text-color-primary); font-size: 27px; }
.manual-cover p { margin: 0 0 16px; color: var(--el-text-color-secondary); font-size: 14px; }
.manual-layout { display: grid; grid-template-columns: 250px minmax(0, 1fr); gap: 18px; align-items: stretch; height: calc(100vh - 270px); min-height: 360px; }
.manual-toc, .manual-body { border: 1px solid var(--el-border-color-lighter); border-radius: 14px; }
.manual-toc { min-height: 0; overflow-y: auto; overscroll-behavior: contain; scrollbar-width: thin; }
.toc-title { margin-bottom: 12px; color: var(--el-text-color-primary); font-size: 15px; font-weight: 700; }
.toc-chapter { margin: 2px 0; }
.toc-link { display: block; padding: 7px 9px; border-radius: 7px; color: var(--el-text-color-regular); font-size: 13px; line-height: 1.5; text-decoration: none; transition: background .15s, color .15s; }
.toc-link:hover { background: var(--el-fill-color-light); color: var(--el-color-primary); }
.toc-footnote { margin-top: 12px; padding: 10px 9px 0; border-top: 1px solid var(--el-border-color-lighter); color: var(--el-text-color-placeholder); font-size: 11px; }
.manual-body { min-width: 0; min-height: 0; height: 100%; overflow-y: auto; overscroll-behavior: contain; scroll-behavior: smooth; scrollbar-width: thin; }
.manual-body :deep(.el-card__body) { padding: 30px 38px; }
.manual-body h1, .manual-body h2, .manual-body h3 { scroll-margin-top: 24px; }
.appendix-title { margin: 32px 0 16px; padding: 15px 18px; border-radius: 10px; background: var(--el-fill-color-light); color: var(--el-text-color-primary); font-size: 21px; }
.chapter-title { display: flex; align-items: center; gap: 11px; margin: 22px 0 16px; padding-bottom: 12px; border-bottom: 1px solid var(--el-border-color-lighter); color: var(--el-text-color-primary); font-size: 20px; line-height: 1.45; }
.chapter-mark { width: 4px; height: 22px; flex: 0 0 auto; border-radius: 4px; background: var(--el-color-primary); }
.section-title { margin: 24px 0 10px; color: var(--el-color-primary); font-size: 15px; line-height: 1.5; }
.manual-body p, .manual-body li { color: var(--el-text-color-regular); font-size: 13px; line-height: 1.9; }
.manual-body p { margin: 9px 0; }
.manual-body ul, .manual-body ol { padding-left: 23px; margin: 8px 0 16px; }
.manual-body li { padding-left: 3px; margin: 4px 0; }
.manual-body blockquote { margin: 14px 0; padding: 12px 16px; border-left: 3px solid var(--el-color-primary); border-radius: 0 8px 8px 0; background: var(--el-fill-color-light); color: var(--el-text-color-regular); line-height: 1.8; }
.manual-body pre { overflow-x: auto; padding: 15px; border-radius: 9px; background: #202a26; color: #e6eee8; font-size: 12px; line-height: 1.7; }
.table-wrap { overflow-x: auto; margin: 14px 0 20px; border: 1px solid var(--el-border-color-lighter); border-radius: 9px; }
.manual-body table { width: 100%; border-collapse: collapse; font-size: 12px; }
.manual-body th, .manual-body td { min-width: 120px; padding: 11px 13px; border-bottom: 1px solid var(--el-border-color-lighter); text-align: left; vertical-align: top; line-height: 1.7; }
.manual-body th { background: var(--el-fill-color-light); color: var(--el-text-color-primary); font-weight: 700; }
.manual-body td { color: var(--el-text-color-regular); }
.manual-body tr:last-child td { border-bottom: 0; }
.manual-body hr { margin: 24px 0; border: 0; border-top: 1px solid var(--el-border-color-lighter); }
@media (max-width: 900px) { .manual-layout { grid-template-columns: 1fr; grid-template-rows: minmax(130px, 30%) minmax(0, 1fr); height: calc(100vh - 230px); min-height: 420px; } .manual-toc { min-height: 0; } .manual-body :deep(.el-card__body) { padding: 22px; } }
</style>
