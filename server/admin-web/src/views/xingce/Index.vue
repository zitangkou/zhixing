<template>
  <div class="page">
    <div class="toolbar">
      <el-upload :show-file-list="false" accept=".json" :http-request="onUpload" :disabled="importing">
        <el-button type="primary" :loading="importing">上传试卷 JSON</el-button>
      </el-upload>
      <el-select v-model="paperType" placeholder="卷种（可留空，读 JSON）" clearable style="width: 220px">
        <el-option v-for="name in allowedTypes" :key="name" :label="name" :value="name" />
      </el-select>
      <el-button :disabled="!dataDirReady || importing" @click="onBundled">从服务器目录导入</el-button>
      <el-button @click="downloadSample">下载示例 JSON</el-button>
      <el-button @click="load">刷新</el-button>
    </div>

    <el-alert type="info" :closable="false" class="hint" :title="hint" />

    <div class="stats">
      <el-tag>入库题位 {{ positionTotal }}</el-tag>
      <el-tag type="success">学员可练 {{ practiceableTotal }}</el-tag>
      <el-tag v-for="item in modules" :key="item.name" effect="plain">{{ item.name }} {{ item.count }}</el-tag>
    </div>

    <ListState :loading="loading" :error="loadError" :has-data="papers.length > 0" empty-text="还没有行测试卷，请上传 JSON" @retry="load">
      <el-table :data="papers" stripe>
        <el-table-column prop="year" label="年份" width="90" />
        <el-table-column prop="paperType" label="卷种" width="120" />
        <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
        <el-table-column prop="positionCount" label="题位" width="80" />
        <el-table-column prop="practiceableCount" label="可练" width="80" />
        <el-table-column label="学员端" width="100">
          <template #default="{ row }">
            <el-tag :type="row.visibleOnHub ? 'success' : 'info'" size="small">
              {{ row.visibleOnHub ? '可见' : '未露出' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="模块" min-width="240">
          <template #default="{ row }">
            <span v-for="mod in row.modules" :key="mod.name" class="mod">{{ mod.name }} {{ mod.count }}</span>
          </template>
        </el-table-column>
      </el-table>
    </ListState>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { UploadRequestOptions } from 'element-plus'
import { ElMessage } from 'element-plus'
import { fetchXingceOverview, importXingceBundled, importXingceJson } from '@/api/xingce'
import type { XingceModuleCount, XingcePaperRow } from '@/api/xingce'
import ListState from '@/components/ListState.vue'
import { useAdminList } from '@/composables/useAdminList'

const SAMPLE = {
  exam_year: 2025,
  exam_name: '2025年国家公务员考试《行测》省级样题',
  paper_type: '省级',
  schema_version: '2',
  total_questions: 1,
  sections: [
    {
      name: '政治理论',
      questions: [
        {
          number: 1,
          section: '政治理论',
          stem: '样题：下列哪一项是中国共产党的根本宗旨？',
          options: { A: '全心全意为人民服务', B: '选项B', C: '选项C', D: '选项D' },
          answer: 'A',
          explanation: '示例解析。正式卷请使用与 import_xingce_2025.py 相同的 JSON。',
        },
      ],
    },
  ],
}

const { loading, loadError, runLoad } = useAdminList()
const papers = ref<XingcePaperRow[]>([])
const modules = ref<XingceModuleCount[]>([])
const positionTotal = ref(0)
const practiceableTotal = ref(0)
const dataDir = ref('')
const dataDirReady = ref(false)
const allowedTypes = ref<string[]>(['省级', '市地级', '行政执法类'])
const paperType = ref('')
const importing = ref(false)

const hint = computed(() => {
  const dir = dataDir.value
    ? `服务器目录：${dataDir.value}${dataDirReady.value ? '（已发现 JSON，可点「从服务器目录导入」）' : '（当前没有卷文件，请上传 JSON）'}`
    : ''
  return `上传单卷 JSON，或把 xingce-structured-data/2025/xingce/papers 放到服务器后导入。学员端只展示 2023–2026 且带答案、无高风险标记的题。${dir}`
})

async function load() {
  await runLoad(async () => {
    const data = await fetchXingceOverview()
    papers.value = data.papers || []
    modules.value = data.modules || []
    positionTotal.value = data.positionTotal || 0
    practiceableTotal.value = data.practiceableTotal || 0
    dataDir.value = data.dataDir || ''
    dataDirReady.value = !!data.dataDirReady
    if (data.allowedPaperTypes?.length) allowedTypes.value = data.allowedPaperTypes
  })
}

async function onUpload(options: UploadRequestOptions) {
  const file = options.file as File
  importing.value = true
  try {
    const stats = await importXingceJson(file, paperType.value || undefined)
    const created = stats.newPositions || 0
    ElMessage.success(created ? `已导入，新题位 ${created}` : '导入完成（内容未变化）')
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '导入失败')
  } finally {
    importing.value = false
  }
}

async function onBundled() {
  importing.value = true
  try {
    const stats = await importXingceBundled()
    ElMessage.success(`目录导入完成，新题位 ${stats.newPositions || 0}`)
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '导入失败')
  } finally {
    importing.value = false
  }
}

function downloadSample() {
  const blob = new Blob([JSON.stringify(SAMPLE, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'xingce-sample-shengji.json'
  link.click()
  URL.revokeObjectURL(url)
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.hint { margin-bottom: 12px; }
.stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.mod { margin-right: 10px; }
</style>
