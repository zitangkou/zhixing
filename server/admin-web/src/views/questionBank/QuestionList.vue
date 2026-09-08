<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">题目资产</h2>
      <el-button @click="load">刷新</el-button>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-select v-model="filters.origin_type" placeholder="来源类型" clearable style="width: 130px" @change="onFilterChange">
        <el-option v-for="o in ORIGIN_TYPE_OPTIONS" :key="o.value" :value="o.value" :label="o.label" />
      </el-select>
      <el-select v-model="filters.module" placeholder="模块" clearable filterable style="width: 160px" @change="onFilterChange">
        <el-option v-for="m in MODULE_OPTIONS" :key="m" :value="m" :label="m" />
      </el-select>
      <el-input v-model="filters.subtype" placeholder="子题型" clearable style="width: 130px" @keyup.enter="onFilterChange" />
      <el-input-number v-model="filters.exam_year" :min="2000" :max="2030" placeholder="年份" clearable style="width: 120px" @change="onFilterChange" />
      <el-select v-model="filters.paper_type" placeholder="卷种" clearable style="width: 130px" @change="onFilterChange">
        <el-option value="省级" label="省级" />
        <el-option value="市地级" label="市地级" />
        <el-option value="行政执法类" label="行政执法类" />
      </el-select>
      <el-select v-model="filters.has_answer" placeholder="是否有答案" clearable style="width: 130px" @change="onFilterChange">
        <el-option :value="true" label="有答案" />
        <el-option :value="false" label="缺答案" />
      </el-select>
      <el-select v-model="filters.review_status" placeholder="审核状态" clearable style="width: 140px" @change="onFilterChange">
        <el-option v-for="o in REVIEW_STATUS_OPTIONS" :key="o.value" :value="o.value" :label="o.label" />
      </el-select>
      <el-input v-model="filters.quality_flag" placeholder="质量flag" clearable style="width: 130px" @keyup.enter="onFilterChange" />
    </div>

    <ListState :loading="loading" :error="loadError" :has-data="items.length > 0" empty-text="暂无题目">
      <el-table :data="items" v-loading="loading && items.length > 0" row-key="id" style="width: 100%">
        <el-table-column prop="id" label="ID" width="180" show-overflow-tooltip />
        <el-table-column label="题干摘要" min-width="220">
          <template #default="{ row }">
            <span :class="{ 'text-danger': !row.has_answer }">{{ row.stem_summary }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="120" show-overflow-tooltip />
        <el-table-column prop="subtype" label="子题型" width="110" show-overflow-tooltip />
        <el-table-column label="答案" width="70">
          <template #default="{ row }">
            <el-tag v-if="row.has_answer" type="success" size="small">{{ row.answer }}</el-tag>
            <el-tag v-else type="danger" size="small">缺答案</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="difficulty" label="难度" width="60" />
        <el-table-column label="来源" width="80">
          <template #default="{ row }">
            <el-tag :type="originTagType(row.origin_type)" size="small">{{ originLabel(row.origin_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.lifecycle_status)" size="small">{{ LIFECYCLE_LABELS[row.lifecycle_status] || row.lifecycle_status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="关联试卷" width="80" align="center">
          <template #default="{ row }">{{ row.paper_count }}</template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="160">
          <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="goDetail(row.id)">查看</el-button>
            <el-button v-if="row.lifecycle_status !== 'active'" link type="success" @click="onPublish(row)">发布</el-button>
            <el-button v-else link type="warning" @click="onUnpublish(row)">下线</el-button>
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import ListState from '@/components/ListState.vue'
import {
  fetchQBQuestions,
  publishQBQuestion,
  unpublishQBQuestion,
  ORIGIN_TYPE_OPTIONS,
  REVIEW_STATUS_OPTIONS,
  LIFECYCLE_LABELS,
  MODULE_OPTIONS,
  type QBQuestionSummary,
} from '@/api/questionBank'

const router = useRouter()

const loading = ref(false)
const loadError = ref('')
const items = ref<QBQuestionSummary[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const filters = reactive({
  origin_type: '',
  module: '',
  subtype: '',
  exam_year: undefined as number | undefined,
  paper_type: '',
  has_answer: undefined as boolean | undefined,
  review_status: '',
  quality_flag: '',
})

function onFilterChange() {
  page.value = 1
  load()
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await fetchQBQuestions({
      page: page.value,
      page_size: pageSize.value,
      origin_type: filters.origin_type || undefined,
      module: filters.module || undefined,
      subtype: filters.subtype || undefined,
      exam_year: filters.exam_year,
      paper_type: filters.paper_type || undefined,
      has_answer: filters.has_answer,
      review_status: filters.review_status || undefined,
      quality_flag: filters.quality_flag || undefined,
    })
    items.value = res.items
    total.value = res.total
  } catch (e: unknown) {
    loadError.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

function goDetail(id: string) {
  router.push(`/question-bank/questions/${id}`)
}

async function onPublish(row: QBQuestionSummary) {
  try {
    await ElMessageBox.confirm(`确认发布题目「${row.stem_summary}」？`, '发布确认', { type: 'warning' })
    const res = await publishQBQuestion(row.id)
    if (res.warnings?.length) {
      ElMessage.warning(res.warnings.join('；'))
    } else {
      ElMessage.success('发布成功')
    }
    row.lifecycle_status = 'active'
  } catch (e: unknown) {
    if (e !== 'cancel') {
      ElMessage.error(e instanceof Error ? e.message : '发布失败')
    }
  }
}

async function onUnpublish(row: QBQuestionSummary) {
  try {
    await ElMessageBox.confirm(`确认下线题目「${row.stem_summary}」？`, '下线确认', { type: 'warning' })
    await unpublishQBQuestion(row.id)
    ElMessage.success('已下线')
    row.lifecycle_status = 'retired'
  } catch (e: unknown) {
    if (e !== 'cancel') {
      ElMessage.error(e instanceof Error ? e.message : '下线失败')
    }
  }
}

function originLabel(t: string) {
  return ORIGIN_TYPE_OPTIONS.find((o) => o.value === t)?.label || t
}

function originTagType(t: string) {
  if (t === 'real') return 'success'
  if (t === 'generated') return 'warning'
  return 'info'
}

function statusTagType(s: string) {
  if (s === 'active') return 'success'
  if (s === 'retired') return 'info'
  if (s === 'disputed') return 'danger'
  return 'info'
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
.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
  padding: 12px;
  background: var(--admin-page-bg);
  border-radius: 6px;
}
.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.text-danger {
  color: var(--el-color-danger);
}
</style>
