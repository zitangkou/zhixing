<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">生成工作台</h2>
      <div class="header-actions">
        <el-button @click="loadAll">刷新</el-button>
        <el-button type="primary" @click="showRunDialog = true">触发生成</el-button>
        <el-button @click="goReview">审核工作台</el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid" v-loading="statsLoading">
      <div class="stat-card">
        <div class="stat-label">总生成题数</div>
        <div class="stat-value">{{ stats.total_generated }}</div>
        <div class="stat-sub">{{ stats.batch_count }} 个批次</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">自动校验通过率</div>
        <div class="stat-value">{{ (stats.auto_pass_rate * 100).toFixed(1) }}%</div>
        <div class="stat-sub">通过 {{ stats.auto_passed }} / 失败 {{ stats.auto_failed }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">待审核</div>
        <div class="stat-value stat-warning">{{ stats.pending_review }}</div>
        <div class="stat-sub">需教研处理</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">已通过 / 已驳回</div>
        <div class="stat-value">
          <span class="stat-success">{{ stats.approved }}</span>
          <span class="stat-divider">/</span>
          <span class="stat-danger">{{ stats.rejected }}</span>
        </div>
        <div class="stat-sub">已发布 {{ stats.published }}</div>
      </div>
    </div>

    <!-- 批次列表 -->
    <div class="section-title">生成批次</div>
    <ListState :loading="batchLoading" :error="batchError" :has-data="batches.length > 0" empty-text="暂无生成批次">
      <el-table :data="batches" v-loading="batchLoading && batches.length > 0" style="width: 100%">
        <el-table-column prop="batch_id" label="批次 ID" width="260" show-overflow-tooltip />
        <el-table-column label="引擎类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ ENGINE_TYPE_LABELS[row.engine_type] || row.engine_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="template_version" label="模板版本" width="200" show-overflow-tooltip />
        <el-table-column prop="total_questions" label="题数" width="70" align="center" />
        <el-table-column label="通过率" width="120">
          <template #default="{ row }">
            <el-progress :percentage="Math.round(row.pass_rate * 100)" :stroke-width="8" />
          </template>
        </el-table-column>
        <el-table-column label="通过/失败" width="100" align="center">
          <template #default="{ row }">
            <span class="text-success">{{ row.passed_count }}</span>
            <span class="text-muted"> / </span>
            <span class="text-danger">{{ row.failed_count }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : 'warning'" size="small">
              {{ row.status === 'completed' ? '已完成' : row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="goDetail(row.batch_id)">查看详情</el-button>
            <el-button link type="success" @click="goReview(row.batch_id)">审核</el-button>
          </template>
        </el-table-column>
      </el-table>
    </ListState>

    <!-- 触发生成弹窗 -->
    <el-dialog v-model="showRunDialog" title="触发生成" width="480px">
      <el-form :model="runForm" label-width="100px">
        <el-form-item label="引擎类型">
          <el-select v-model="runForm.engine_type" style="width: 100%">
            <el-option value="qa_data_analysis" label="资料分析" />
            <el-option value="qa_quantity" label="数量关系" />
          </el-select>
        </el-form-item>
        <el-form-item label="技能/题型">
          <el-input v-model="runForm.skill" placeholder="可选，如：基期量、工程问题" />
        </el-form-item>
        <el-form-item label="生成数量">
          <el-input-number v-model="runForm.count" :min="1" :max="100" />
        </el-form-item>
        <el-form-item label="随机种子">
          <el-input-number v-model="runForm.seed" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRunDialog = false">取消</el-button>
        <el-button type="primary" :loading="runLoading" @click="onRun">确认生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import ListState from '@/components/ListState.vue'
import {
  fetchGenStats,
  fetchGenBatches,
  runGenBatch,
  ENGINE_TYPE_LABELS,
  type GenStats,
  type GenBatchSummary,
} from '@/api/generation'

const router = useRouter()

const stats = ref<GenStats>({
  total_generated: 0, auto_pass_rate: 0, auto_passed: 0, auto_failed: 0,
  pending_review: 0, approved: 0, rejected: 0, published: 0, batch_count: 0, by_engine: {},
})
const statsLoading = ref(false)
const batches = ref<GenBatchSummary[]>([])
const batchLoading = ref(false)
const batchError = ref('')

const showRunDialog = ref(false)
const runLoading = ref(false)
const runForm = reactive({ engine_type: 'qa_data_analysis', skill: '', count: 10, seed: 42 })

async function loadStats() {
  statsLoading.value = true
  try {
    stats.value = await fetchGenStats()
  } catch (e: any) {
    batchError.value = e.message || '加载统计失败'
  } finally {
    statsLoading.value = false
  }
}

async function loadBatches() {
  batchLoading.value = true
  batchError.value = ''
  try {
    const res = await fetchGenBatches({ page: 1, page_size: 50 })
    batches.value = res.items
  } catch (e: any) {
    batchError.value = e.message || '加载批次失败'
  } finally {
    batchLoading.value = false
  }
}

function loadAll() {
  loadStats()
  loadBatches()
}

function goDetail(batchId: string) {
  router.push(`/generation/batches/${batchId}`)
}

function goReview(batchId?: string) {
  if (batchId) {
    router.push({ path: '/generation/review', query: { batch_id: batchId } })
  } else {
    router.push('/generation/review')
  }
}

async function onRun() {
  runLoading.value = true
  try {
    const res = await runGenBatch({ ...runForm })
    ElMessage.success(res.message)
    showRunDialog.value = false
    loadAll()
  } catch (e: any) {
    ElMessage.error(e.message || '触发生成失败')
  } finally {
    runLoading.value = false
  }
}

function formatTime(t: string | null) {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 19)
}

onMounted(loadAll)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-title { margin: 0; font-size: 18px; font-weight: 600; }
.header-actions { display: flex; gap: 8px; }

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
.stat-card {
  background: var(--admin-page-bg, #f5f7fa);
  border-radius: 8px;
  padding: 20px;
}
.stat-label { font-size: 13px; color: var(--el-text-color-secondary); margin-bottom: 8px; }
.stat-value { font-size: 28px; font-weight: 700; color: var(--el-text-color-primary); }
.stat-sub { font-size: 12px; color: var(--el-text-color-secondary); margin-top: 6px; }
.stat-warning { color: var(--el-color-warning); }
.stat-success { color: var(--el-color-success); }
.stat-danger { color: var(--el-color-danger); }
.stat-divider { color: var(--el-text-color-secondary); margin: 0 4px; }

.section-title {
  font-size: 15px;
  font-weight: 600;
  margin: 8px 0 12px;
  color: var(--el-text-color-primary);
}
.text-success { color: var(--el-color-success); }
.text-danger { color: var(--el-color-danger); }
.text-muted { color: var(--el-text-color-secondary); }
</style>
