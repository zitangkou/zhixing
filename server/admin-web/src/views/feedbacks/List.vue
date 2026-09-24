<template>
  <div class="page">
    <div class="toolbar">
      <el-select v-model="status" placeholder="状态" clearable style="width: 140px" @change="reload">
        <el-option label="待处理" value="new" />
        <el-option label="已采纳" value="adopted" />
        <el-option label="已驳回" value="rejected" />
      </el-select>
      <el-button type="primary" @click="reload">查询</el-button>
    </div>

    <ListState :loading="loading" :error="loadError" :has-data="items.length > 0" empty-text="暂无反馈" @retry="load">
      <el-table v-loading="loading && items.length > 0" :data="items" stripe>
        <el-table-column prop="createdAt" label="时间" width="170" :formatter="formatTime" />
        <el-table-column prop="username" label="用户" width="120" show-overflow-tooltip />
        <el-table-column prop="content" label="内容" min-width="280" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link size="small" @click="openDetail(row)">查看</el-button>
            <el-button v-if="canHandle && row.status === 'new'" link size="small" type="primary" @click="openHandle(row, 'adopted')">
              采纳
            </el-button>
            <el-button v-if="canHandle && row.status === 'new'" link size="small" type="danger" @click="openHandle(row, 'rejected')">
              驳回
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </ListState>

    <div v-if="total > size" class="pager">
      <el-pagination
        v-model:current-page="page"
        :page-size="size"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="load"
      />
    </div>

    <el-drawer v-model="detailVisible" title="反馈详情" size="420px">
      <template v-if="current">
        <p class="meta">{{ current.username || current.userId }} · {{ statusLabel(current.status) }}</p>
        <p class="meta">{{ formatTime(current) }}</p>
        <p class="content">{{ current.content }}</p>
        <p v-if="current.note" class="note">处理备注：{{ current.note }}</p>
        <div v-if="canHandle && current.status === 'new'" class="detail-actions">
          <el-button type="primary" @click="openHandle(current, 'adopted')">采纳</el-button>
          <el-button type="danger" plain @click="openHandle(current, 'rejected')">驳回</el-button>
        </div>
      </template>
    </el-drawer>

    <el-dialog v-model="handleVisible" :title="handleAction === 'adopted' ? '采纳反馈' : '驳回反馈'" width="420px">
      <el-form label-position="top">
        <el-form-item v-if="handleAction === 'adopted'" label="加分">
          <el-input-number v-model="points" :min="0" :max="100" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="note" type="textarea" :rows="3" maxlength="256" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="handleVisible = false">取消</el-button>
        <el-button type="primary" :loading="handling" @click="onHandle">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { handleFeedback, listFeedbacks } from '@/api/feedbacks'
import type { FeedbackItem } from '@/api/feedbacks'
import ListState from '@/components/ListState.vue'
import { useAdminList } from '@/composables/useAdminList'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const canHandle = computed(() => auth.hasPermission('feedback:write'))
const { loading, loadError, runLoad } = useAdminList()
const items = ref<FeedbackItem[]>([])
const total = ref(0)
const page = ref(1)
const size = 20
const status = ref('')

const detailVisible = ref(false)
const current = ref<FeedbackItem | null>(null)
const handleVisible = ref(false)
const handleAction = ref<'adopted' | 'rejected'>('adopted')
const note = ref('')
const points = ref(10)
const handling = ref(false)

function statusLabel(value: string) {
  if (value === 'adopted') return '已采纳'
  if (value === 'rejected') return '已驳回'
  return '待处理'
}

function statusTag(value: string) {
  if (value === 'adopted') return 'success'
  if (value === 'rejected') return 'info'
  return 'warning'
}

function formatTime(row: FeedbackItem) {
  return (row.createdAt || '').slice(0, 16).replace('T', ' ')
}

async function load() {
  await runLoad(async () => {
    const data = await listFeedbacks({
      status: status.value || undefined,
      page: page.value,
      size,
    })
    items.value = data.items || []
    total.value = data.total || 0
  })
}

function reload() {
  page.value = 1
  void load()
}

function openDetail(row: FeedbackItem) {
  current.value = row
  detailVisible.value = true
}

function openHandle(row: FeedbackItem, action: 'adopted' | 'rejected') {
  current.value = row
  handleAction.value = action
  note.value = ''
  points.value = action === 'adopted' ? 10 : 0
  handleVisible.value = true
}

async function onHandle() {
  if (!current.value) return
  handling.value = true
  try {
    await handleFeedback(current.value.id, {
      action: handleAction.value,
      note: note.value.trim(),
      points: handleAction.value === 'adopted' ? points.value : 0,
    })
    ElMessage.success(handleAction.value === 'adopted' ? '已采纳' : '已驳回')
    handleVisible.value = false
    detailVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '处理失败')
  } finally {
    handling.value = false
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
  flex-wrap: wrap;
}
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
.meta {
  margin: 0 0 8px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.content {
  margin: 12px 0;
  white-space: pre-wrap;
  line-height: 1.6;
}
.note {
  color: var(--el-text-color-regular);
}
.detail-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}
</style>
