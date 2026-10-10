<template>
  <div class="page">
    <div class="heading">
      <div><h2>人民日报采集批次</h2><p>每日 06:10（北京时间）检查电子报目录；来源未发布时每 10 分钟重试至 08:00。手动补采可选择任意刊期。</p></div>
      <div class="run-controls"><el-date-picker v-model="issueDate" type="date" value-format="YYYY-MM-DD" /><el-button type="primary" :loading="running" @click="runNow">立即采集</el-button><el-button @click="load">刷新</el-button></div>
    </div>
    <el-alert type="info" :closable="false" class="note" title="采集器收录人民日报电子报版面与文章目录，并从人民日报客户端首页/评论页补充发现来源。默认只保存元数据、原文链接和来源证据；全文留待审核与保存等级判定后单独采集。" />
    <el-card shadow="never">
      <el-table :data="batches" v-loading="loading" row-key="id">
        <el-table-column prop="issueDate" label="刊期" width="120" />
        <el-table-column label="触发方式" width="110"><template #default="{ row }">{{ row.triggerMode === 'scheduled' ? '定时' : '手动' }}</template></el-table-column>
        <el-table-column label="状态" width="145"><template #default="{ row }"><el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag></template></el-table-column>
        <el-table-column label="版面进度" width="150"><template #default="{ row }">{{ row.completedPageCount }} / {{ row.expectedPageCount || '—' }}<small v-if="row.failedPageCount">版面失败 {{ row.failedPageCount }}</small><small v-if="row.failedSourceCount">来源失败 {{ row.failedSourceCount }}</small></template></el-table-column>
        <el-table-column prop="discoveredArticleCount" label="发现文章" width="100" />
        <el-table-column prop="createdArticleCount" label="新增档案" width="100" />
        <el-table-column prop="startedAt" label="开始时间" min-width="170"><template #default="{ row }">{{ formatTime(row.startedAt) }}</template></el-table-column>
        <el-table-column label="错误/说明" min-width="240" show-overflow-tooltip><template #default="{ row }">{{ row.errorSummary || '—' }}</template></el-table-column>
      </el-table>
      <el-empty v-if="!loading && batches.length === 0" description="尚无采集批次" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listRmrbArchiveBatches, runRmrbArchiveBatch, type RmrbArchiveBatch } from '@/api/rmrbArchive'

const loading = ref(false)
const running = ref(false)
const batches = ref<RmrbArchiveBatch[]>([])
const issueDate = ref(new Date().toLocaleDateString('sv-SE'))
let refreshTimer: ReturnType<typeof setInterval> | undefined
function statusLabel(status: string) {
  return ({ queued: '排队中', running: '采集中', waiting_for_source: '等待来源更新', completed: '已完成', partial: '部分完成', failed: '失败' } as Record<string, string>)[status] || status
}
function statusType(status: string) {
  return status === 'completed' ? 'success' : status === 'failed' ? 'danger' : status === 'partial' ? 'warning' : 'info'
}
function formatTime(value?: string | null) { return value ? value.replace('T', ' ').slice(0, 16) : '—' }
async function load() {
  loading.value = true
  try { batches.value = await listRmrbArchiveBatches() }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '批次列表加载失败') }
  finally { loading.value = false }
}
async function runNow() {
  if (!issueDate.value) return ElMessage.warning('请先选择出版日期')
  running.value = true
  try {
    await runRmrbArchiveBatch(issueDate.value)
    ElMessage.success('采集批次已提交，后台运行中')
    await load()
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '提交采集失败') }
  finally { running.value = false }
}
onMounted(() => { void load(); refreshTimer = setInterval(() => void load(), 15000) })
onUnmounted(() => { if (refreshTimer) clearInterval(refreshTimer) })
</script>

<style scoped>
.heading { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 16px; }
.heading h2 { margin: 0 0 6px; font-size: 20px; }
.heading p { margin: 0; color: var(--el-text-color-secondary); font-size: 13px; }
.run-controls { display: flex; gap: 8px; align-items: center; }
.note { margin-bottom: 16px; }
small { display: block; color: var(--el-text-color-secondary); }
</style>
