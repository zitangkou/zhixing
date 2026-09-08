<template>
  <div class="page">
    <div class="page-header">
      <div class="header-left">
        <el-button link @click="goBack" style="padding: 0; margin-right: 12px">← 返回</el-button>
        <h2 class="page-title">教研审核工作台</h2>
      </div>
      <div class="header-actions">
        <el-button @click="load">刷新</el-button>
        <el-button v-if="selectedIds.length > 0" type="success" @click="onBatchApprove">
          批量通过 ({{ selectedIds.length }})
        </el-button>
        <el-button v-if="selectedIds.length > 0" type="danger" @click="onBatchReject">
          批量驳回 ({{ selectedIds.length }})
        </el-button>
      </div>
    </div>

    <!-- 审核统计 -->
    <div class="review-stats" v-if="stats">
      <div class="rs-item">
        <div class="rs-label">总数</div>
        <div class="rs-value">{{ stats.total }}</div>
      </div>
      <div class="rs-item rs-warning">
        <div class="rs-label">待审核</div>
        <div class="rs-value">{{ stats.pending }}</div>
      </div>
      <div class="rs-item rs-success">
        <div class="rs-label">已通过</div>
        <div class="rs-value">{{ stats.approved }}</div>
      </div>
      <div class="rs-item rs-danger">
        <div class="rs-label">已驳回</div>
        <div class="rs-value">{{ stats.rejected }}</div>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-select v-model="filters.status" placeholder="审核状态" clearable style="width: 130px" @change="load">
        <el-option value="pending" label="待审核" />
        <el-option value="approve" label="已通过" />
        <el-option value="reject" label="已驳回" />
      </el-select>
      <el-select v-model="filters.engine_type" placeholder="引擎类型" clearable style="width: 140px" @change="load">
        <el-option value="qa_data_analysis" label="资料分析" />
        <el-option value="qa_quantity" label="数量关系" />
      </el-select>
      <el-select v-model="filters.module" placeholder="模块" clearable style="width: 130px" @change="load">
        <el-option value="资料分析" label="资料分析" />
        <el-option value="数量关系" label="数量关系" />
      </el-select>
      <el-input v-model="filters.subtype" placeholder="子题型" clearable style="width: 140px" @keyup.enter="load" />
      <el-select v-model="filters.difficulty" placeholder="难度" clearable style="width: 100px" @change="load">
        <el-option v-for="d in [1,2,3,4,5]" :key="d" :value="d" :label="`难度 ${d}`" />
      </el-select>
    </div>

    <!-- 题目列表 -->
    <ListState :loading="loading" :error="loadError" :has-data="items.length > 0" empty-text="暂无待审核题目">
      <el-table
        :data="items"
        v-loading="loading && items.length > 0"
        row-key="question_id"
        @selection-change="onSelectionChange"
        style="width: 100%"
      >
        <el-table-column type="selection" width="45" />
        <el-table-column prop="question_id" label="题号" width="200" show-overflow-tooltip />
        <el-table-column label="引擎" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ ENGINE_TYPE_LABELS[row.engine_type] || row.engine_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="subtype" label="子题型" width="130" show-overflow-tooltip />
        <el-table-column prop="difficulty" label="难度" width="60" align="center" />
        <el-table-column label="题干摘要" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ row.stem_summary }}</template>
        </el-table-column>
        <el-table-column label="答案" width="60">
          <template #default="{ row }">
            <el-tag type="primary" size="small">{{ row.answer }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="双求解" width="70" align="center">
          <template #default="{ row }">
            <el-icon v-if="row.dual_solve_match" color="var(--el-color-success)"><CircleCheckFilled /></el-icon>
            <el-icon v-else color="var(--el-color-danger)"><CircleCloseFilled /></el-icon>
          </template>
        </el-table-column>
        <el-table-column label="审核状态" width="90">
          <template #default="{ row }">
            <el-tag :type="REVIEW_STATUS_TYPES[row.review_status] as any" size="small">
              {{ REVIEW_STATUS_LABELS[row.review_status] || row.review_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row.question_id)">查看详情</el-button>
            <el-button link type="success" @click="onApprove(row)">通过</el-button>
            <el-button link type="danger" @click="onReject(row)">驳回</el-button>
          </template>
        </el-table-column>
      </el-table>
    </ListState>

    <div class="pagination-bar">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="load"
        @current-change="load"
      />
    </div>

    <!-- 审核弹窗 -->
    <el-dialog v-model="showReviewDialog" :title="`审核题目 - ${currentQuestionId}`" width="700px" top="5vh">
      <div class="review-dialog-content">
        <QuestionDetailPanel v-if="currentQuestionId" :question-id="currentQuestionId" />
        <div class="review-form">
          <el-form label-width="80px">
            <el-form-item label="审核意见">
              <el-input v-model="reviewComment" type="textarea" :rows="3" placeholder="请输入审核意见（可选）" />
            </el-form-item>
            <el-form-item label="审核人">
              <el-input v-model="reviewer" placeholder="审核人姓名" />
            </el-form-item>
          </el-form>
        </div>
      </div>
      <template #footer>
        <el-button @click="showReviewDialog = false">取消</el-button>
        <el-button type="danger" :loading="reviewLoading" @click="submitReview('reject')">驳回</el-button>
        <el-button type="success" :loading="reviewLoading" @click="submitReview('approve')">通过</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheckFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import ListState from '@/components/ListState.vue'
import QuestionDetailPanel from './components/QuestionDetailPanel.vue'
import {
  fetchGenReviewTasks,
  reviewGenQuestion,
  batchReviewGenQuestions,
  ENGINE_TYPE_LABELS,
  REVIEW_STATUS_LABELS,
  REVIEW_STATUS_TYPES,
  type GenQuestionSummary,
} from '@/api/generation'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const loadError = ref('')
const items = ref<GenQuestionSummary[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const stats = ref<{ total: number; pending: number; approved: number; rejected: number } | null>(null)
const selectedIds = ref<string[]>([])

const filters = reactive({
  status: route.query.status as string || 'pending',
  engine_type: '',
  module: '',
  subtype: '',
  difficulty: undefined as number | undefined,
})

const showReviewDialog = ref(false)
const currentQuestionId = ref('')
const reviewComment = ref('')
const reviewer = ref('')
const reviewLoading = ref(false)

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await fetchGenReviewTasks({
      status: filters.status || undefined,
      engine_type: filters.engine_type || undefined,
      module: filters.module || undefined,
      subtype: filters.subtype || undefined,
      difficulty: filters.difficulty,
      page: page.value,
      page_size: pageSize.value,
    })
    items.value = res.items
    total.value = res.total
    stats.value = res.stats
  } catch (e: any) {
    loadError.value = e.message || '加载审核任务失败'
  } finally {
    loading.value = false
  }
}

function onSelectionChange(rows: GenQuestionSummary[]) {
  selectedIds.value = rows.map((r) => r.question_id)
}

function openDetail(qid: string) {
  currentQuestionId.value = qid
  reviewComment.value = ''
  showReviewDialog.value = true
}

function onApprove(row: GenQuestionSummary) {
  currentQuestionId.value = row.question_id
  reviewComment.value = ''
  showReviewDialog.value = true
}

function onReject(row: GenQuestionSummary) {
  currentQuestionId.value = row.question_id
  reviewComment.value = ''
  showReviewDialog.value = true
}

async function submitReview(action: 'approve' | 'reject') {
  if (!currentQuestionId.value) return
  reviewLoading.value = true
  try {
    const res = await reviewGenQuestion(currentQuestionId.value, {
      action,
      comment: reviewComment.value,
      reviewer: reviewer.value || 'admin',
    })
    ElMessage.success(res.message)
    showReviewDialog.value = false
    load()
  } catch (e: any) {
    ElMessage.error(e.message || '审核提交失败')
  } finally {
    reviewLoading.value = false
  }
}

async function onBatchApprove() {
  if (!selectedIds.value.length) return
  try {
    await ElMessageBox.confirm(`确认批量通过 ${selectedIds.value.length} 道题？`, '批量审核', { type: 'success' })
    await batchReviewGenQuestions({
      action: 'approve',
      comment: '批量通过',
      reviewer: reviewer.value || 'admin',
      question_ids: selectedIds.value,
    })
    ElMessage.success('批量通过成功')
    selectedIds.value = []
    load()
  } catch { /* cancelled */ }
}

async function onBatchReject() {
  if (!selectedIds.value.length) return
  try {
    await ElMessageBox.confirm(`确认批量驳回 ${selectedIds.value.length} 道题？`, '批量审核', { type: 'warning' })
    await batchReviewGenQuestions({
      action: 'reject',
      comment: '批量驳回',
      reviewer: reviewer.value || 'admin',
      question_ids: selectedIds.value,
    })
    ElMessage.success('批量驳回成功')
    selectedIds.value = []
    load()
  } catch { /* cancelled */ }
}

function goBack() {
  router.push('/generation')
}

onMounted(load)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.header-left { display: flex; align-items: center; }
.page-title { margin: 0; font-size: 18px; font-weight: 600; }
.header-actions { display: flex; gap: 8px; }

.review-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.rs-item {
  background: var(--admin-page-bg, #f5f7fa);
  border-radius: 8px;
  padding: 14px;
  text-align: center;
}
.rs-label { font-size: 12px; color: var(--el-text-color-secondary); margin-bottom: 4px; }
.rs-value { font-size: 24px; font-weight: 700; }
.rs-warning .rs-value { color: var(--el-color-warning); }
.rs-success .rs-value { color: var(--el-color-success); }
.rs-danger .rs-value { color: var(--el-color-danger); }

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
  padding: 12px;
  background: var(--admin-page-bg, #f5f7fa);
  border-radius: 6px;
}
.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.review-dialog-content { display: flex; flex-direction: column; gap: 16px; max-height: 60vh; overflow-y: auto; }
.review-form { padding: 0 8px; }
</style>
