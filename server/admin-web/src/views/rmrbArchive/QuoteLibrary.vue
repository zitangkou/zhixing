<template>
  <div class="page">
    <header>
      <div>
        <h2>金句管理</h2>
        <p>先审核是否符合金句素材，通过后再启用；仿写可在确认运营用途时按需生成。</p>
      </div>
      <div class="actions">
        <el-button v-if="canWrite" :loading="running || jobActive" :disabled="jobActive" @click="run">整理今日</el-button>
        <el-button type="primary" @click="edit()">新增</el-button>
      </div>
    </header>

    <el-alert v-if="job" :type="job.status === 'completed' ? 'success' : job.status === 'partial' || job.status === 'failed' ? 'warning' : job.status === 'empty' ? 'info' : 'info'" :closable="false">
      <template #title>今日采集：{{ jobStatusLabel(job.status) }}<span v-if="job.error"> · {{ job.error }}</span></template>
      <div v-if="job.metrics" class="job-metrics">
        纸版文章 {{ job.metrics.paperDiscovered ?? 0 }} / 入选 {{ job.metrics.paperSelected ?? 0 }} / 正文处理 {{ job.metrics.paperFetched ?? 0 }}；
        客户端评论 {{ job.metrics.peopleappDiscovered ?? 0 }} / 正文处理 {{ job.metrics.peopleappFetched ?? 0 }}；
        候选句 {{ job.metrics.candidateQuotes ?? 0 }} / 质量拒绝 {{ job.metrics.qualityRejected ?? 0 }}（考生视角不符 {{ job.metrics.roleFitRejected ?? 0 }} · 缺少适配依据 {{ job.metrics.roleFitReasonRejected ?? 0 }}） / 重复 {{ job.metrics.duplicates ?? 0 }} / 新增 {{ job.metrics.quotesSaved ?? 0 }} / 库内 {{ job.metrics.quotesInDatabase ?? 0 }}
      </div>
      <el-collapse v-if="job.directory?.length" class="directory-inspection">
        <el-collapse-item :title="`逐篇范围复核：纳入 ${directorySummary(job.directory)} / ${job.directory.length}`" name="directory">
          <el-table :data="job.directory" size="small" max-height="320">
            <el-table-column label="文章 / 版面" min-width="300">
              <template #default="{ row }"><div>{{ row.title }}</div><div class="meta">第{{ row.pageNo ?? row.page ?? '—' }}版 · {{ row.pageName || '栏目未标注' }}</div></template>
            </el-table-column>
            <el-table-column label="分类" width="120"><template #default="{ row }">{{ categoryLabel(row.category) }}</template></el-table-column>
            <el-table-column label="处理" width="100"><template #default="{ row }">{{ row.included ? '进入正文复核' : '目录排除' }}</template></el-table-column>
            <el-table-column label="依据" width="180"><template #default="{ row }">{{ row.classificationFallback ? '分类服务失败，降级处理' : row.classificationSource === 'analysis_cache' ? '复用分析缓存' : row.classificationSource === 'title_column_rule' ? '标题/栏目规则' : '目录模型' }}</template></el-table-column>
            <el-table-column label="正文与选句" min-width="190">
              <template #default="{ row }"><div>{{ processStatusLabel(row.processStatus, row.included) }}</div><div v-if="row.candidateCount !== undefined" class="meta">候选 {{ row.candidateCount }} · 通过校验 {{ row.acceptedCount ?? 0 }} · 入库 {{ row.savedCount ?? 0 }}</div><div v-if="row.processError || row.rejectionReasons?.length" class="meta">{{ row.processError || [...new Set(row.rejectionReasons)].join('、') }}</div></template>
            </el-table-column>
          </el-table>
        </el-collapse-item>
      </el-collapse>
      <div v-if="job.zeroReason" class="job-reason">零结果原因：{{ job.zeroReason }}</div>
      <div v-if="job.failures?.length" class="job-reason">
        <div>失败 {{ job.failures.length }} 项，可重试：</div>
        <div v-for="(failure, index) in job.failures.slice(0, 3)" :key="`${failure.url || failure.source}-${index}`">
          {{ failure.source || failure.url || '采集任务' }} · {{ failure.stage || '处理' }} · {{ failure.code || 'unknown' }}：{{ failure.error || '未提供详情' }}
        </div>
      </div>
      <div v-if="job.warnings?.length" class="job-reason">
        <div v-for="(warning, index) in job.warnings.slice(0, 3)" :key="`${warning.url || warning.source}-${warning.code}-${index}`">
          提示：{{ warning.source || warning.url || '采集任务' }} · {{ warning.code }}{{ warning.message ? `：${warning.message}` : '' }}
        </div>
      </div>
    </el-alert>
    <el-alert v-else-if="jobConfig && !jobConfig.llmConfigured" type="warning" :closable="false" title="今日自动整理尚未启动：服务端 LLM 未启用或未配置。" />
    <el-alert v-else-if="jobConfig && !jobConfig.enabled" type="info" :closable="false" title="每日金句自动整理已关闭，可由有写权限的管理员手动启动。" />
    <el-alert v-else-if="jobConfig" type="info" :closable="false" :title="`今日任务尚未入队；默认计划 ${jobConfig.schedule}，上游延迟时最迟于北京时间 08:30 独立启动。`" />

    <div class="filters">
      <el-radio-group v-model="status" @change="filter">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="pending">待确认</el-radio-button>
        <el-radio-button value="confirmed">已启用</el-radio-button>
      </el-radio-group>
      <el-input v-model="search" clearable placeholder="搜索原句" @keyup.enter="filter" @clear="filter" />
      <el-date-picker v-model="selectionDate" type="date" value-format="YYYY-MM-DD" placeholder="采集日期" @change="filter" />
    </div>

    <el-alert type="info" :closable="false" title="勾选已启用金句并保存当日精选，可记录入选特征与未入选原因；单条退回也需说明原因。系统只把跨多个刊期反复出现的理由用于后续候选排序。" />
    <div class="selection-bar">
      <div><strong>当日精选：{{ selection.length }} 条</strong><span class="meta">　选中理由（用于校准后续推荐）</span></div>
      <el-checkbox-group v-model="selectionReasons" class="reason-group">
        <el-checkbox-button v-for="option in selectionReasonOptions" :key="option.value" :value="option.value">{{ option.label }}</el-checkbox-button>
      </el-checkbox-group>
      <div class="meta">未入选主要原因</div>
      <el-checkbox-group v-model="notSelectedReasons" class="reason-group">
        <el-checkbox-button v-for="option in rejectionReasonOptions" :key="option.value" :value="option.value">{{ option.label }}</el-checkbox-button>
      </el-checkbox-group>
      <el-button v-if="canWrite" type="primary" :disabled="!selection.length && !hasExistingSelection" @click="saveDailySelection">保存当日精选</el-button>
    </div>

    <el-table ref="tableRef" v-loading="loading" :data="items" row-key="id" @selection-change="selection = $event">
      <el-table-column type="selection" width="48" :selectable="canSelect" />
      <el-table-column label="金句" min-width="280">
        <template #default="{ row }">
          <div class="quote">{{ row.text }}</div>
          <div class="meta">{{ row.topics.join('、') || row.component }} · {{ row.articleTitle }}</div>
          <div v-if="row.roleFitReason" class="meta">考生视角：{{ row.roleFitReason }}</div>
          <div v-if="row.humanFeedback" class="meta feedback">人工反馈：入选 {{ row.humanFeedback.selected }} 次 · 未入选 {{ row.humanFeedback.notSelected }} 次 · 退回 {{ row.humanFeedback.rejected }} 次<span v-if="row.humanFeedback.selectedReasons?.length"> · 入选特征：{{ feedbackReasonLabels(row.humanFeedback.selectedReasons) }}</span><span v-if="row.humanFeedback.notSelectedReasons?.length"> · 未入选原因：{{ feedbackReasonLabels(row.humanFeedback.notSelectedReasons) }}</span><span v-if="row.humanFeedback.reasons?.length"> · 退回原因：{{ feedbackReasonLabels(row.humanFeedback.reasons) }}</span></div>
        </template>
      </el-table-column>
      <el-table-column label="AI初筛" width="150">
        <template #default="{ row }">
          <template v-if="row.scores && Object.keys(row.scores).length"><span>{{ scoreSummary(row.scores) }}</span><div class="meta">推荐 {{ row.recommendationScore ?? '—' }}/5</div></template>
          <span v-else class="meta">—</span>
        </template>
      </el-table-column>
      <el-table-column label="日期" width="170">
        <template #default="{ row }">
          <div>文章：{{ row.articleDate || '—' }}</div>
          <div class="meta">采集：{{ row.collectedDate || '—' }}</div>
        </template>
      </el-table-column>
      <el-table-column label="审核" width="90">
        <template #default="{ row }">{{ auditLabel(row.auditStatus) }}</template>
      </el-table-column>
      <el-table-column label="启用" width="90">
        <template #default="{ row }">{{ row.enabled ? '已启用' : '未启用' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="340">
        <template #default="{ row }">
          <el-button link @click="edit(row)">编辑</el-button>
          <el-button link @click="audit(row)">审核</el-button>
          <el-button v-if="!row.enabled" link type="primary" @click="enable(row)">启用</el-button>
          <el-button v-if="canWrite && row.enabled && !row.examples.length" link type="primary" :disabled="row.examplesStatus === 'generating'" @click="generateExamples(row)">{{ row.examplesStatus === 'generating' ? '生成中' : row.examplesStatus === 'failed' ? '重试仿写' : '生成仿写' }}</el-button>
          <el-button v-if="row.enabled" link @click="disable(row)">停用</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" :total="total" :page-size="100" layout="total, prev, pager, next" @current-change="load" />

    <el-drawer v-model="editing" title="金句" size="480px">
      <el-form v-if="draft" label-position="top">
        <el-form-item label="原句"><el-input v-model="draft.text" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="主题（逗号分隔）"><el-input v-model="topicsInput" /></el-form-item>
        <el-form-item label="构件">
          <el-select v-model="draft.component" style="width: 100%">
            <el-option v-for="c in components" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="重点词（逗号分隔）"><el-input v-model="highlightsInput" /></el-form-item>
        <el-form-item label="句式"><el-input v-model="draft.formula" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="用法"><el-input v-model="draft.use" /></el-form-item>
        <el-form-item label="为什么好"><el-input v-model="draft.why" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="考生视角适配依据"><el-input v-model="draft.roleFitReason" type="textarea" :rows="2" maxlength="120" show-word-limit /></el-form-item>
        <el-form-item label="怎么用"><el-input v-model="draft.guidance" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="注意"><el-input v-model="draft.pitfall" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="出处栏目"><el-input v-model="draft.source" /></el-form-item>
        <el-form-item label="文章标题"><el-input v-model="draft.articleTitle" /></el-form-item>
        <el-form-item label="原文链接"><el-input v-model="draft.sourceUrl" /></el-form-item>
        <el-form-item label="证据摘录（须包含原句，确认前必填）"><el-input v-model="draft.evidence" type="textarea" :rows="4" /></el-form-item>
        <div v-for="(ex, n) in draft.examples" :key="n" class="example">
          <el-input v-model="ex.topic" placeholder="仿写主题" />
          <el-input v-model="ex.text" type="textarea" :rows="3" placeholder="仿写" />
          <el-button link type="danger" @click="draft.examples.splice(n, 1)">移除</el-button>
        </div>
        <el-button @click="draft.examples.push({ topic: '', text: '', shortText: '', highlights: [] })">加一条仿写</el-button>
        <div class="save"><el-button type="primary" :loading="saving" @click="save">保存</el-button></div>
      </el-form>
    </el-drawer>

    <el-dialog v-model="reviewVisible" title="金句复核反馈" width="620px">
      <template v-if="reviewTarget">
        <blockquote class="review-quote">{{ reviewTarget.text }}</blockquote>
        <el-radio-group v-model="reviewDecision">
          <el-radio-button value="passed">符合金句标准</el-radio-button>
          <el-radio-button value="rejected">退回</el-radio-button>
        </el-radio-group>
        <el-form label-position="top" class="review-form">
          <el-form-item label="退回原因（至少选一项，或填写说明）">
            <el-checkbox-group v-model="reviewReasons" class="reason-group">
              <el-checkbox-button v-for="option in rejectionReasonOptions" :key="option.value" :value="option.value">{{ option.label }}</el-checkbox-button>
            </el-checkbox-group>
          </el-form-item>
          <el-form-item label="补充说明"><el-input v-model="reviewNote" type="textarea" :rows="3" maxlength="500" show-word-limit /></el-form-item>
        </el-form>
      </template>
      <template #footer><el-button @click="reviewVisible = false">取消</el-button><el-button type="primary" :loading="reviewSaving" @click="submitReview">保存复核</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import * as api from '@/api/dailyQuotes'

const auth = useAuthStore()
const canWrite = computed(() => auth.hasPermission('rmrb:write'))
const today = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai' }).format(new Date())
const components = ['开头点题', '分论点标题', '论证句', '结尾升华']
const selectionDate = ref(today)
const status = ref('')
const search = ref('')
const page = ref(1)
const total = ref(0)
const items = ref<api.DailyQuote[]>([])
const tableRef = ref()
const selection = ref<api.DailyQuote[]>([])
const hasExistingSelection = ref(false)
const selectionReasons = ref<string[]>([])
const notSelectedReasons = ref<string[]>([])
const selectionReasonOptions = [
  { value: 'student_perspective', label: '贴近考生' },
  { value: 'actionable', label: '具体可落地' },
  { value: 'memorable', label: '有亮点易记' },
  { value: 'theme_balance', label: '主题互补' },
]
const rejectionReasonOptions = [
  { value: 'too_abstract', label: '过于宏观/抽象' },
  { value: 'too_narrow', label: '主题过窄/术语多' },
  { value: 'context_dependent', label: '依赖上下文' },
  { value: 'ordinary_expression', label: '表达普通/亮点不足' },
  { value: 'weak_argument', label: '论证价值弱' },
  { value: 'repetitive', label: '与已选句重复' },
  { value: 'evidence_concern', label: '出处/证据有疑问' },
]
const loading = ref(false)
const saving = ref(false)
const running = ref(false)
const job = ref<api.DailyQuoteJob | null>(null)
const jobConfig = ref<{enabled:boolean;llmConfigured:boolean;schedule:string} | null>(null)
const jobActive = computed(() => ['queued', 'running'].includes(job.value?.status || ''))
let jobPollTimer: ReturnType<typeof setInterval> | undefined
const editing = ref(false)
const reviewVisible = ref(false)
const reviewSaving = ref(false)
const reviewTarget = ref<api.DailyQuote | null>(null)
const reviewDecision = ref<'passed' | 'rejected'>('passed')
const reviewReasons = ref<string[]>([])
const reviewNote = ref('')
const draft = ref<api.DailyQuote | null>(null)
const topicsInput = ref('')
const highlightsInput = ref('')

function split(s: string) {
  return s.split(/[，,]/).map((x) => x.trim()).filter(Boolean)
}

async function load() {
  loading.value = true
  try {
    const data = await api.listQuotes({ q: search.value, status: status.value, start: selectionDate.value, end: selectionDate.value, selection_date: selectionDate.value, page: page.value, page_size: 100 })
    items.value = data.items
    total.value = data.total
    const selectedIds = await api.getSelection(selectionDate.value)
    hasExistingSelection.value = selectedIds.length > 0
    await nextTick()
    for (const row of items.value) tableRef.value?.toggleRowSelection(row, selectedIds.includes(row.id))
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

function filter() {
  page.value = 1
  void load()
}

function edit(row?: api.DailyQuote) {
  draft.value = row
    ? JSON.parse(JSON.stringify(row))
    : {
        id: '', text: '', collectedDate: today, articleDate: today, articleTitle: '', sourceUrl: '',
        source: '', author: '', component: '论证句', quoteType: '完整句', topics: [], use: '', formula: '',
        why: '', guidance: '', pitfall: '', evidence: '', evidenceLocation: '', highlights: [], examples: [],
        reviewStatus: 'pending', auditStatus: 'pending', enabled: false, selected: false,
      }
  topicsInput.value = draft.value!.topics.join('，')
  highlightsInput.value = draft.value!.highlights.join('，')
  editing.value = true
}

async function save() {
  if (!draft.value) return
  saving.value = true
  try {
    draft.value.topics = split(topicsInput.value)
    draft.value.highlights = split(highlightsInput.value)
    await api.saveQuote(draft.value)
    editing.value = false
    await load()
    ElMessage.success('已保存')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function generateExamples(row: api.DailyQuote) {
  try {
    await api.generateExamples(row.id)
    ElMessage.success('已提交仿写生成；稍后刷新查看')
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '提交失败')
  }
}

function auditLabel(s: string) {
  return ({ pending: '待审核', passed: '符合', rejected: '不符合' } as Record<string, string>)[s] || '待审核'
}

function jobStatusLabel(s: string) {
  return ({ queued: '排队中', running: '处理中', completed: '完成', partial: '部分完成', empty: '无合格金句', failed: '失败' } as Record<string, string>)[s] || s
}

async function refreshJob() {
  try {
    const data = await api.getQuoteJob(today)
    const wasActive = jobActive.value
    job.value = data.job
    jobConfig.value = { enabled: data.enabled, llmConfigured: data.llmConfigured, schedule: data.schedule }
    if (jobActive.value && !jobPollTimer) jobPollTimer = setInterval(() => { void refreshJob() }, 3000)
    if (!jobActive.value && jobPollTimer) {
      clearInterval(jobPollTimer)
      jobPollTimer = undefined
      if (wasActive) void load()
    }
  } catch {
    // 任务状态提示不影响金句列表的正常使用。
  }
}

async function audit(row: api.DailyQuote) {
  reviewTarget.value = row
  reviewDecision.value = row.auditStatus === 'rejected' ? 'rejected' : 'passed'
  reviewReasons.value = []
  reviewNote.value = ''
  reviewVisible.value = true
}

async function submitReview() {
  if (!reviewTarget.value) return
  reviewSaving.value = true
  try {
    await api.reviewQuote(reviewTarget.value.id, { decision: reviewDecision.value, reason_codes: reviewReasons.value, note: reviewNote.value })
    reviewVisible.value = false
    await load()
    ElMessage.success(reviewDecision.value === 'passed' ? '已记录复核通过' : '已记录退回原因')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存复核失败')
  } finally {
    reviewSaving.value = false
  }
}

function canSelect(row: api.DailyQuote) {
  return row.reviewStatus === 'confirmed' && row.enabled && row.auditStatus === 'passed'
}

function scoreSummary(scores: Record<string, number>) {
  const labels: Record<string, string> = { memory: '记', logic: '论', transfer: '迁', spark: '亮', roleFit: '考生适配' }
  return Object.entries(labels).filter(([key]) => Number.isFinite(scores[key])).map(([key, label]) => `${label}${scores[key]}`).join(' · ')
}

function categoryLabel(category?: string) {
  return ({ core: '评论核心', extended: '扩展观点', unknown: '待正文复核', uncertain: '待正文复核', exclude: '非评论' } as Record<string, string>)[category || ''] || category || '未分类'
}

function processStatusLabel(status?: string, included?: boolean) {
  const labels: Record<string, string> = { running: '处理中', completed: '已处理', candidate_saved: '候选已入库', duplicate: '候选重复', candidate_rejected: '候选未通过校验', no_candidate: '文章未选出金句', not_comment: '正文判为非评论', processed_partial: '部分处理失败', failed: '处理失败' }
  return labels[status || ''] || (included ? '等待正文处理' : '未进入正文处理')
}

function directorySummary(items?: api.DailyQuoteJob['directory']) {
  return items?.filter(item => item.included).length || 0
}

function feedbackReasonLabels(reasons: string[]) {
  const labels = Object.fromEntries([...selectionReasonOptions, ...rejectionReasonOptions].map(x => [x.value, x.label]))
  return [...new Set(reasons)].map(reason => labels[reason] || reason).join('、')
}

async function saveDailySelection() {
  const perArticle = new Map<string, number>()
  const perTopic = new Map<string, number>()
  for (const row of selection.value) perArticle.set(row.articleTitle, (perArticle.get(row.articleTitle) || 0) + 1)
  for (const row of selection.value) {
    const topic = row.topics[0]
    if (topic) perTopic.set(topic, (perTopic.get(topic) || 0) + 1)
  }
  const concentrated = [...perArticle.values()].some(count => count > 2) || [...perTopic.values()].some(count => count > 2)
  if (concentrated) {
    try { await ElMessageBox.confirm('当前同一篇文章或同一主题选中了3句或更多。仍可保存，但建议检查整组来源与主题是否过于集中。', '精选组合提醒', { confirmButtonText: '仍然保存', cancelButtonText: '返回调整', type: 'warning' }) }
    catch { return }
  }
  try {
    await api.saveSelection(selectionDate.value, selection.value.map(row => row.id), selectionReasons.value, notSelectedReasons.value)
    hasExistingSelection.value = selection.value.length > 0
    await load()
    ElMessage.success('当日精选与人工选择理由已记录')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存精选失败')
  }
}

async function enable(row: api.DailyQuote) {
  if (row.auditStatus !== 'passed') {
    ElMessage.warning('请先审核通过')
    return
  }
  try {
    await api.saveQuote({ ...row, auditStatus: 'passed', enabled: true, reviewStatus: 'confirmed' })
    await load()
    ElMessage.success('已启用')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '启用失败')
  }
}

async function disable(row: api.DailyQuote) {
  await api.saveQuote({ ...row, enabled: false, reviewStatus: 'pending' })
  await load()
}

async function remove(row: api.DailyQuote) {
  try {
    await ElMessageBox.confirm('删除后学员端不再显示。', '删除金句', { type: 'warning' })
    await api.deleteQuote(row.id)
    await load()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error(e instanceof Error ? e.message : '删除失败')
  }
}

async function run() {
  running.value = true
  try {
    await api.runQuoteJob(today)
    ElMessage.success('已开始整理，完成后出现在待确认')
    await refreshJob()
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '整理失败')
  } finally {
    running.value = false
  }
}

onMounted(() => { void load(); void refreshJob() })
onBeforeUnmount(() => { if (jobPollTimer) clearInterval(jobPollTimer) })
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.job-metrics, .job-reason { margin-top: 6px; line-height: 1.6; }
header, .actions, .filters { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
header { justify-content: space-between; }
header p { margin: 4px 0 0; color: var(--el-text-color-secondary); }
.filters .el-input { width: 220px; }
.quote { line-height: 1.6; }
.meta { margin-top: 4px; color: var(--el-text-color-secondary); font-size: 12px; }
.feedback { color: var(--el-color-primary); }
.directory-inspection { margin-top: 8px; }
.selection-bar { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; padding: 12px 14px; border: 1px solid var(--el-border-color-light); border-radius: 8px; background: var(--el-fill-color-lighter); }
.reason-group { display: flex; flex-wrap: wrap; gap: 6px; }
.review-quote { margin: 0 0 18px; padding: 12px 16px; border-left: 3px solid var(--el-color-primary); background: var(--el-fill-color-lighter); line-height: 1.8; }
.review-form { margin-top: 18px; }
.example { display: flex; flex-direction: column; gap: 8px; margin: 12px 0; }
.save { margin-top: 16px; }
</style>
