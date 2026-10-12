<template>
  <div class="project-manual-page">
    <el-card shadow="never" class="manual-cover">
      <div class="cover-eyebrow">ZHIXING · OPERATIONS</div>
      <h1>项目功能与操作</h1>
      <p>集中查看各小程序、H5、共享后端和管理后台的功能边界、日常操作及发布步骤。</p>
      <el-alert
        title="本文是全仓操作手册；知行公考的详细页面与路由清单仍以 FEATURES.md 为准。"
        type="info"
        :closable="false"
        show-icon
      />
    </el-card>

    <el-card shadow="never" class="manual-body">
      <template v-for="(block, index) in blocks" :key="index">
        <h1 v-if="block.type === 'heading' && block.level === 1">{{ block.text }}</h1>
        <h2 v-else-if="block.type === 'heading' && block.level === 2">{{ block.text }}</h2>
        <h3 v-else-if="block.type === 'heading'">{{ block.text }}</h3>
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
</template>

<script setup lang="ts">
import { computed } from 'vue'
import manualSource from '../../../../../docs/PROJECT_OPERATIONS_MANUAL.md?raw'

type ManualBlock =
  | { type: 'heading'; level: number; text: string }
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
      blocks.push({ type: 'heading', level: heading[1].length, text: cleanInline(heading[2]) })
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
</script>

<style scoped>
.project-manual-page { max-width: 1180px; margin: 0 auto; }
.manual-cover { margin-bottom: 16px; border: 0; border-radius: 14px; }
.cover-eyebrow { color: #6b8278; font-size: 11px; font-weight: 700; letter-spacing: 1.5px; }
.manual-cover h1 { margin: 8px 0; color: #263b34; font-size: 24px; }
.manual-cover p { margin: 0 0 16px; color: #68756e; }
.manual-body { border: 0; border-radius: 14px; }
.manual-body h1 { margin: 12px 0 16px; font-size: 24px; color: #243a33; }
.manual-body h2 { margin: 30px 0 12px; padding-bottom: 8px; border-bottom: 1px solid #e8ece8; font-size: 19px; color: #2c4b40; }
.manual-body h3 { margin: 22px 0 10px; font-size: 15px; color: #3d554b; }
.manual-body p, .manual-body li { color: #4d5a54; font-size: 13px; line-height: 1.8; }
.manual-body p { margin: 8px 0; }
.manual-body ul, .manual-body ol { padding-left: 22px; margin: 7px 0 14px; }
.manual-body blockquote { margin: 12px 0; padding: 10px 14px; border-left: 3px solid #7b9b88; background: #f4f7f4; color: #58675e; line-height: 1.7; }
.manual-body pre { overflow-x: auto; padding: 14px; border-radius: 9px; background: #202a26; color: #e6eee8; font-size: 12px; line-height: 1.6; }
.table-wrap { overflow-x: auto; margin: 12px 0 18px; }
.manual-body table { width: 100%; border-collapse: collapse; font-size: 12px; }
.manual-body th, .manual-body td { min-width: 130px; padding: 10px 12px; border: 1px solid #e5e9e5; text-align: left; vertical-align: top; line-height: 1.6; }
.manual-body th { background: #f3f6f3; color: #344e42; font-weight: 700; }
.manual-body td { color: #4d5a54; }
.manual-body hr { margin: 22px 0; border: 0; border-top: 1px solid #e8ece8; }
</style>
