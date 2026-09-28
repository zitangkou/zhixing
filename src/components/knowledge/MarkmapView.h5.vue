<template>
  <view class="mm-h5">
    <svg ref="svgEl" class="mm-svg" />
  </view>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { KnowledgeMapNode } from '@/types'
import {
  KNOWLEDGE_MAP_THEME,
  branchColor,
  escapeHtml,
  wrapTitle,
} from '@/constants/knowledgeMapTheme'

const props = defineProps<{
  tree: KnowledgeMapNode | null
}>()

const svgEl = ref<SVGSVGElement | null>(null)
let mm: { destroy: () => void; setData: (d: unknown) => Promise<void>; fit: () => Promise<void> } | null =
  null
const branchIndexByPath = new Map<string, number>()

function assignBranches(root: KnowledgeMapNode) {
  branchIndexByPath.clear()
  ;(root.children || []).forEach((c, i) => {
    const mark = (n: KnowledgeMapNode, idx: number) => {
      branchIndexByPath.set(n.path, idx)
      for (const ch of n.children || []) mark(ch, idx)
    }
    mark(c, i)
  })
}

function toPure(n: KnowledgeMapNode) {
  const content = escapeHtml(wrapTitle(n.title)).replace(/&lt;br&gt;/gi, '<br>')
  return {
    content,
    children: (n.children || []).map(toPure),
    payload: { path: n.path, depth: n.depth, id: n.id },
  }
}

async function ensure() {
  if (!svgEl.value || mm) return
  const { Markmap } = await import('markmap-view')
  assignBranches(props.tree || { id: '', title: '', depth: 0, line: 0, path: '', children: [] })
  mm = Markmap.create(svgEl.value, {
    autoFit: true,
    duration: 300,
    initialExpandLevel: 2,
    zoom: true,
    pan: true,
    maxWidth: KNOWLEDGE_MAP_THEME.maxWidth,
    paddingX: KNOWLEDGE_MAP_THEME.paddingX,
    spacingHorizontal: KNOWLEDGE_MAP_THEME.spacingHorizontal,
    spacingVertical: KNOWLEDGE_MAP_THEME.spacingVertical,
    color: (node: { payload?: { depth?: number; path?: string }; state?: { depth?: number } }) => {
      const depth = node.payload?.depth ?? node.state?.depth ?? 0
      const path = node.payload?.path || ''
      return branchColor(depth, branchIndexByPath.get(path) ?? 0)
    },
    lineWidth: (node: { state?: { depth?: number } }) =>
      KNOWLEDGE_MAP_THEME.lineWidth(node.state?.depth ?? 0),
  }) as typeof mm
}

async function render() {
  await nextTick()
  await ensure()
  if (!mm) return
  if (!props.tree) {
    await mm.setData(null)
    return
  }
  assignBranches(props.tree)
  await mm.setData(toPure(props.tree))
  await mm.fit()
}

onMounted(() => {
  void render()
})

watch(
  () => props.tree,
  () => {
    void render()
  },
  { deep: true },
)

onBeforeUnmount(() => {
  mm?.destroy()
  mm = null
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.mm-h5 {
  width: 100%;
  height: 420px;
  background: $card-bg;
  border-radius: $radius-md;
  overflow: hidden;
}
.mm-svg {
  width: 100%;
  height: 100%;
  display: block;
}
</style>
