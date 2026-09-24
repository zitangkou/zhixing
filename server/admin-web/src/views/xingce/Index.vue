<template>
  <div class="page">
    <div class="toolbar">
      <el-upload :show-file-list="false" accept=".json" :http-request="onUpload" :disabled="importing">
        <el-button type="primary" :loading="importing">上传 JSON</el-button>
      </el-upload>
      <el-select v-model="filter" style="width: 180px">
        <el-option label="全部" value="" />
        <el-option-group label="年份">
          <el-option v-for="year in yearOptions" :key="year" :label="String(year)" :value="`y:${year}`" />
        </el-option-group>
        <el-option-group label="卷种">
          <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="`t:${item.value}`" />
        </el-option-group>
      </el-select>
    </div>

    <ListState
      :loading="loading"
      :error="loadError"
      :has-data="papers.length > 0"
      empty-text="还没有行测试卷，请上传 JSON"
      @retry="load"
    >
      <el-table :data="visiblePapers" stripe>
        <el-table-column prop="year" label="年份" width="90" />
        <el-table-column prop="paperType" label="卷种" width="120" />
        <el-table-column prop="title" label="标题" min-width="240" show-overflow-tooltip />
        <el-table-column prop="positionCount" label="题位" width="90" />
        <el-table-column prop="practiceableCount" label="可练" width="90" />
      </el-table>
    </ListState>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { UploadRequestOptions } from 'element-plus'
import { ElMessage } from 'element-plus'
import { fetchXingceOverview, importXingceJson } from '@/api/xingce'
import type { XingcePaperRow } from '@/api/xingce'
import ListState from '@/components/ListState.vue'
import { useAdminList } from '@/composables/useAdminList'

const TYPE_OPTIONS = [
  { label: '省级', value: '省级' },
  { label: '市地', value: '市地级' },
  { label: '行政执法', value: '行政执法类' },
]

const { loading, loadError, runLoad } = useAdminList()
const papers = ref<XingcePaperRow[]>([])
const filter = ref('')
const importing = ref(false)

const yearOptions = computed(() => {
  const years = new Set<number>([2023, 2024, 2025, 2026])
  for (const paper of papers.value) years.add(paper.year)
  return [...years].sort((a, b) => b - a)
})

const typeOptions = TYPE_OPTIONS

const visiblePapers = computed(() => {
  const value = filter.value
  if (!value) return papers.value
  if (value.startsWith('y:')) {
    const year = Number(value.slice(2))
    return papers.value.filter((paper) => paper.year === year)
  }
  if (value.startsWith('t:')) {
    const paperType = value.slice(2)
    return papers.value.filter((paper) => paper.paperType === paperType)
  }
  return papers.value
})

async function load() {
  await runLoad(async () => {
    const data = await fetchXingceOverview()
    papers.value = data.papers || []
  })
}

async function onUpload(options: UploadRequestOptions) {
  const file = options.file as File
  importing.value = true
  try {
    const stats = await importXingceJson(file)
    const created = stats.newPositions || 0
    ElMessage.success(created ? `已导入，新题位 ${created}` : '导入完成（内容未变化）')
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '导入失败')
  } finally {
    importing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
</style>
