<template>
  <div class="page">
    <div class="page-header">
      <div class="header-left">
        <el-button link @click="goBack" style="padding: 0; margin-right: 12px">← 返回</el-button>
        <h2 class="page-title">批次详情</h2>
      </div>
      <el-button @click="load">刷新</el-button>
    </div>

    <div v-loading="loading">
      <!-- 批次元信息 -->
      <div class="meta-card" v-if="batch">
        <div class="meta-row">
          <div class="meta-item"><span class="meta-label">批次 ID：</span>{{ batch.batch_id }}</div>
          <div class="meta-item"><span class="meta-label">引擎：</span>
            <el-tag size="small">{{ ENGINE_TYPE_LABELS[batch.engine_type] || batch.engine_type }}</el-tag>
          </div>
          <div class="meta-item"><span class="meta-label">模板版本：</span>{{ batch.template_version }}</div>
          <div class="meta-item"><span class="meta-label">种子：</span>{{ batch.seed ?? '-' }}</div>
        </div>
        <div class="meta-row">
          <div class="meta-item"><span class="meta-label">创建时间：</span>{{ formatTime(batch.created_at) }}</div>
          <div class="meta-item"><span class="meta-label">状态：</span>
            <el-tag :type="batch.status === 'completed' ? 'success' : 'warning'" size="small">
              {{ batch.status === 'completed' ? '已完成' : batch.status }}
            </el-tag>
          </div>
          <div class="meta-item" v-if="batch.dual_solve_method">
            <span class="meta-label">双求解方式：</span>{{ batch.dual_solve_method }}
          </div>
        </div>
      </div>

      <!-- 校验汇总卡片 -->
      <div class="validation-summary" v-if="batch">
        <div class="vs-item">
          <div class="vs-label">总题数</div>
          <div class="vs-value">{{ batch.total_questions }}</div>
        </div>
        <div class="vs-item">
          <div class="vs-label">校验通过</div>
          <div class="vs-value text-success">{{ batch.passed_count }}</div>
        </div>
        <div class="vs-item">
          <div class="vs-label">校验失败</div>
          <div class="vs-value text-danger">{{ batch.failed_count }}</div>
        </div>
        <div class="vs-item">
          <div class="vs-label">通过率</div>
          <div class="vs-value">{{ (batch.pass_rate * 100).toFixed(1) }}%</div>
        </div>
      </div>

      <!-- 校验报告（可展开） -->
      <el-collapse class="validation-collapse" v-if="validation">
        <el-collapse-item title="自动校验报告明细" name="validation">
          <div class="failure-dist" v-if="Object.keys(validation.failure_distribution).length > 0">
            <span class="fd-label">失败原因分布：</span>
            <el-tag v-for="(count, reason) in validation.failure_distribution" :key="reason" size="small" type="danger" style="margin-right: 6px">
              {{ VALIDATION_CHECK_LABELS[reason] || reason }}: {{ count }}
            </el-tag>
          </div>
          <el-table :data="validation.per_question" size="small" style="margin-top: 12px">
            <el-table-column prop="question_id" label="题号" width="200" />
            <el-table-column prop="subtype" label="子题型" width="140" show-overflow-tooltip />
            <el-table-column prop="difficulty" label="难度" width="60" align="center" />
            <el-table-column v-for="(label, key) in VALIDATION_CHECK_LABELS" :key="key" :label="label" width="90" align="center">
              <template #default="{ row }">
                <el-icon v-if="row.checks[key]" color="var(--el-color-success)"><CircleCheckFilled /></el-icon>
                <el-icon v-else color="var(--el-color-danger)"><CircleCloseFilled /></el-icon>
              </template>
            </el-table-column>
            <el-table-column label="结果" width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="row.all_passed ? 'success' : 'danger'" size="small">
                  {{ row.all_passed ? '通过' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-collapse-item>
      </el-collapse>

      <!-- 题目列表 -->
      <div class="section-title">题目列表（{{ batch?.questions.length || 0 }} 题）</div>
      <ListState :loading="loading" :error="loadError" :has-data="!!batch && batch.questions.length > 0" empty-text="暂无题目">
        <el-table :data="batch?.questions || []" row-key="question_id" style="width: 100%">
          <el-table-column type="expand">
            <template #default="{ row }">
              <QuestionDetailPanel :question-id="row.question_id" />
            </template>
          </el-table-column>
          <el-table-column prop="question_id" label="题号" width="200" show-overflow-tooltip />
          <el-table-column prop="subtype" label="子题型" width="140" show-overflow-tooltip />
          <el-table-column prop="difficulty" label="难度" width="60" align="center" />
          <el-table-column label="答案" width="70">
            <template #default="{ row }">
              <el-tag type="primary" size="small">{{ row.answer }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="双求解" width="80" align="center">
            <template #default="{ row }">
              <el-icon v-if="row.dual_solve_match" color="var(--el-color-success)"><CircleCheckFilled /></el-icon>
              <el-icon v-else color="var(--el-color-danger)"><CircleCloseFilled /></el-icon>
            </template>
          </el-table-column>
          <el-table-column prop="distractor_count" label="干扰项数" width="80" align="center" />
          <el-table-column label="审核状态" width="100">
            <template #default="{ row }">
              <el-tag :type="REVIEW_STATUS_TYPES[row.review_status] as any" size="small">
                {{ REVIEW_STATUS_LABELS[row.review_status] || row.review_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="goQuestion(row.question_id)">查看</el-button>
              <el-button link type="success" @click="goReview(row.question_id)">审核</el-button>
            </template>
          </el-table-column>
        </el-table>
      </ListState>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CircleCheckFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import ListState from '@/components/ListState.vue'
import QuestionDetailPanel from './components/QuestionDetailPanel.vue'
import {
  fetchGenBatchDetail,
  fetchGenValidation,
  ENGINE_TYPE_LABELS,
  REVIEW_STATUS_LABELS,
  REVIEW_STATUS_TYPES,
  VALIDATION_CHECK_LABELS,
  type GenBatchDetail,
  type GenValidationReport,
} from '@/api/generation'

const route = useRoute()
const router = useRouter()
const batchId = route.params.id as string

const loading = ref(false)
const loadError = ref('')
const batch = ref<GenBatchDetail | null>(null)
const validation = ref<GenValidationReport | null>(null)

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    batch.value = await fetchGenBatchDetail(batchId)
    validation.value = await fetchGenValidation(batchId)
  } catch (e: any) {
    loadError.value = e.message || '加载批次详情失败'
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.push('/generation')
}

function goQuestion(qid: string) {
  router.push(`/generation/review?question_id=${qid}`)
}

function goReview(qid: string) {
  router.push({ path: '/generation/review', query: { question_id: qid } })
}

function formatTime(t: string | null) {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 19)
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

.meta-card {
  background: var(--admin-page-bg, #f5f7fa);
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 16px;
}
.meta-row { display: flex; flex-wrap: wrap; gap: 24px; margin-bottom: 8px; }
.meta-row:last-child { margin-bottom: 0; }
.meta-item { font-size: 13px; color: var(--el-text-color-primary); }
.meta-label { color: var(--el-text-color-secondary); }

.validation-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.vs-item {
  background: var(--admin-page-bg, #f5f7fa);
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}
.vs-label { font-size: 12px; color: var(--el-text-color-secondary); margin-bottom: 6px; }
.vs-value { font-size: 22px; font-weight: 700; }

.validation-collapse { margin-bottom: 16px; }
.failure-dist { margin-bottom: 8px; }
.fd-label { font-size: 13px; color: var(--el-text-color-secondary); margin-right: 8px; }

.section-title {
  font-size: 15px;
  font-weight: 600;
  margin: 8px 0 12px;
}
.text-success { color: var(--el-color-success); }
.text-danger { color: var(--el-color-danger); }
</style>
