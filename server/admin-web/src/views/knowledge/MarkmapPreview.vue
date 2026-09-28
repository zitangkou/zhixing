<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { Markmap } from 'markmap-view'
import type { MapNode } from '@/api/knowledge'
import { buildBranchIndex, markmapOptions, renderTreeToPureSvg, toPure, type BranchIndex } from './mapRender'
import type { PureSvg } from './exportMap'

const props = defineProps<{
  tree: MapNode | null
  duration?: number
  initialExpandLevel?: number
}>()

const svgEl = ref<SVGSVGElement | null>(null)
let mm: Markmap | null = null
// 颜色函数按引用读取该 Map，树变化时原地更新即可
const branches: BranchIndex = new Map()

async function ensureMm() {
  if (!svgEl.value || mm) return
  mm = Markmap.create(
    svgEl.value,
    markmapOptions(branches, {
      duration: props.duration ?? 300,
      initialExpandLevel: props.initialExpandLevel ?? -1,
      zoom: true,
      pan: true,
    }),
  )
}

async function render() {
  await nextTick()
  await ensureMm()
  if (!mm) return
  if (!props.tree) {
    await mm.setData(null)
    return
  }
  branches.clear()
  for (const [k, v] of buildBranchIndex(props.tree)) branches.set(k, v)
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

/**
 * 渲染并返回纯 SVG（用于导出）。colorRoot 为全树时，分片沿用全树的分支配色。
 */
async function renderToPureSvg(tree: MapNode, expandLevel = -1, colorRoot?: MapNode): Promise<PureSvg> {
  return renderTreeToPureSvg(tree, {
    expandLevel,
    branches: buildBranchIndex(colorRoot || tree),
  })
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
  font-family: -apple-system, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Noto Sans CJK SC', sans-serif;
}
</style>
