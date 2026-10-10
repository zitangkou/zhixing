<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchImageGenerationJobs, type ImageGenerationJob, type ImageGenerationStatus } from '@/api/imageGenerationJobs'

const rows = ref<ImageGenerationJob[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const size = ref(20)
const status = ref('')

const statusText: Record<ImageGenerationStatus, string> = {
  queued: '排队中', running: '生成中', succeeded: '已完成', failed: '失败',
}
const statusType: Record<ImageGenerationStatus, 'info' | 'warning' | 'success' | 'danger'> = {
  queued: 'info', running: 'warning', succeeded: 'success', failed: 'danger',
}

function formatTime(value: string | null) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'
}

async function load() {
  loading.value = true
  try {
    const result = await fetchImageGenerationJobs({ status: status.value || undefined, page: page.value, size: size.value })
    rows.value = result.items
    total.value = result.total
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '生成记录加载失败')
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  page.value = 1
  load()
}

onMounted(load)
</script>

<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>
        <div class="card-head">
          <div>
            <div class="title">图片生成记录</div>
            <div class="subtitle">查看异步任务进度与失败原因。密钥、提示词和原图不会显示在此页。</div>
          </div>
          <div class="actions">
            <el-select v-model="status" clearable placeholder="全部状态" style="width: 140px" @change="onFilterChange">
              <el-option label="排队中" value="queued" />
              <el-option label="生成中" value="running" />
              <el-option label="已完成" value="succeeded" />
              <el-option label="失败" value="failed" />
            </el-select>
            <el-button :loading="loading" @click="load">刷新</el-button>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column label="状态" width="110">
          <template #default="{ row }"><el-tag :type="statusType[row.status]">{{ statusText[row.status] }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="userName" label="用户" min-width="130" />
        <el-table-column prop="styleId" label="风格 ID" min-width="150" />
        <el-table-column label="模型" min-width="150"><template #default="{ row }">{{ row.modelId || '风格默认模型' }}<span v-if="row.provider" class="muted"> · {{ row.provider }}</span></template></el-table-column>
        <el-table-column prop="productKey" label="产品" width="100" />
        <el-table-column prop="id" label="任务 ID" min-width="220" show-overflow-tooltip />
        <el-table-column label="失败原因" min-width="280">
          <template #default="{ row }">
            <div v-if="row.errorMessage" class="failure-detail">
              <el-tag type="danger" size="small">{{ row.errorCode || 'failed' }}</el-tag>
              <span>{{ row.errorMessage }}</span>
            </div>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="提交时间" min-width="175"><template #default="{ row }">{{ formatTime(row.createdAt) }}</template></el-table-column>
        <el-table-column label="完成时间" min-width="175"><template #default="{ row }">{{ formatTime(row.completedAt) }}</template></el-table-column>
        <template #empty><el-empty description="暂无图片生成记录" /></template>
      </el-table>
      <div class="pagination"><el-pagination v-model:current-page="page" v-model:page-size="size" :total="total" layout="total, sizes, prev, pager, next" @current-change="load" @size-change="onFilterChange" /></div>
    </el-card>
  </div>
</template>

<style scoped>
.card-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.title { font-size: 16px; font-weight: 600; }
.subtitle { margin-top: 6px; color: var(--el-text-color-secondary); font-size: 13px; }
.actions { display: flex; align-items: center; gap: 10px; }
.failure-detail { display: flex; align-items: flex-start; gap: 8px; white-space: normal; line-height: 1.5; }
.pagination { display: flex; justify-content: flex-end; margin-top: 18px; }
.muted { color: var(--el-text-color-secondary); }
</style>
