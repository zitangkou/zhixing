<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { Markmap } from 'markmap-view'
import type { INode, IPureNode } from 'markmap-common'
import type { MapNode } from '@/api/knowledge'
import { KNOWLEDGE_MAP_THEME, branchColor, escapeHtml, wrapTitle } from './mapTheme'
import { svgToPureSvg } from './exportMap'

const props = defineProps<{
  tree: MapNode | null
  duration?: number
  initialExpandLevel?: number
}>()

const svgEl = ref<SVGSVGElement | null>(null)
let mm: Markmap | null = null
const branchIndexByPath = new Map<string, number>()

function assignBranches(root: MapNode) {
  branchIndexByPath.clear()
  ;(root.children || []).forEach((c, i) => {
    const mark = (n: MapNode, idx: number) => {
      branchIndexByPath.set(n.path, idx)
      for (const ch of n.children || []) mark(ch, idx)
    }
    mark(c, i)
  })
}

function toPure(n: MapNode): IPureNode {
  const wrapped = wrapTitle(n.title)
  const content = escapeHtml(wrapped).replace(/&lt;br&gt;/gi, '<br>')
  return {
    content,
    children: (n.children || []).map(toPure),
    payload: { line: n.line, path: n.path, id: n.id, depth: n.depth },
  }
}

function colorOf(node: INode): string {
  const depth = (node.payload as { depth?: number } | undefined)?.depth ?? node.state?.depth ?? 0
  const path = (node.payload as { path?: string } | undefined)?.path || ''
  const bi = branchIndexByPath.get(path) ?? 0
  return branchColor(depth, bi)
}

async function ensureMm() {
  if (!svgEl.value) return
  if (mm) return
  mm = Markmap.create(svgEl.value, {
    autoFit: true,
    duration: props.duration ?? 300,
    initialExpandLevel: props.initialExpandLevel ?? -1,
    zoom: true,
    pan: true,
    maxWidth: KNOWLEDGE_MAP_THEME.maxWidth,
    paddingX: KNOWLEDGE_MAP_THEME.paddingX,
    spacingHorizontal: KNOWLEDGE_MAP_THEME.spacingHorizontal,
    spacingVertical: KNOWLEDGE_MAP_THEME.spacingVertical,
    color: colorOf,
    lineWidth: (node) => KNOWLEDGE_MAP_THEME.lineWidth(node.state?.depth ?? 0),
  })
}

async function render() {
  await nextTick()
  await ensureMm()
  if (!mm) return
  if (!props.tree) {
    await mm.setData(null)
    return
  }
  assignBranches(props.tree)
  mm.setOptions({
    duration: props.duration ?? 300,
    initialExpandLevel: props.initialExpandLevel ?? -1,
  })
  await mm.setData(toPure(props.tree))
  await mm.fit()
}

watch(
  () => props.tree,
  () => {
    void render()
  },
  { deep: true, immediate: true },
)

onBeforeUnmount(() => {
  mm?.destroy()
  mm = null
})

async function fit() {
  await mm?.fit()
}

/** 在隐藏容器中渲染并返回纯 SVG 字符串（用于导出）。 */
async function renderToPureSvg(tree: MapNode, expandLevel = -1): Promise<string> {
  const host = document.createElement('div')
  host.style.cssText = 'position:fixed;left:-99999px;top:0;width:1200px;height:900px;opacity:0;pointer-events:none'
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
  svg.setAttribute('width', '1200')
  svg.setAttribute('height', '900')
  host.appendChild(svg)
  document.body.appendChild(host)
  assignBranches(tree)
  const temp = Markmap.create(svg, {
    autoFit: true,
    duration: 0,
    initialExpandLevel: expandLevel,
    zoom: false,
    pan: false,
    maxWidth: KNOWLEDGE_MAP_THEME.maxWidth,
    paddingX: KNOWLEDGE_MAP_THEME.paddingX,
    spacingHorizontal: KNOWLEDGE_MAP_THEME.spacingHorizontal,
    spacingVertical: KNOWLEDGE_MAP_THEME.spacingVertical,
    color: colorOf,
    lineWidth: (node) => KNOWLEDGE_MAP_THEME.lineWidth(node.state?.depth ?? 0),
  })
  try {
    await temp.setData(toPure(tree))
    await temp.fit()
    // 等一帧让 layout 稳定
    await new Promise((r) => requestAnimationFrame(() => r(undefined)))
    return svgToPureSvg(svg)
  } finally {
    temp.destroy()
    host.remove()
  }
}

defineExpose({ fit, renderToPureSvg })
</script>

<template>
  <div class="mm-wrap">
    <svg ref="svgEl" class="mm-svg" />
  </div>
</template>

<style scoped>
.mm-wrap {
  width: 100%;
  height: 100%;
  min-height: 360px;
  background: #fff;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  overflow: hidden;
}
.mm-svg {
  width: 100%;
  height: 100%;
  display: block;
}
</style>
