<template>
  <div class="vocabulary-page">
    <div class="toolbar">
      <h2>人民日报联合素材采集</h2>
      <el-button @click="rulesVisible = true">筛选规则</el-button>
      <el-button :loading="loading" @click="refresh">刷新</el-button>
    </div>
    <el-alert title="同批分析人民日报全文，联合生成金句、词汇和申论素材候选；正文与分析结果复用，不重复发送全文。三类物料分别执行来源校验、去重并进入人工审核，不会自动发布。" type="info" :closable="false" />
    <div class="toolbar filters">
      <el-date-picker v-model="filters.issue_date" type="date" value-format="YYYY-MM-DD" placeholder="文章日期" @change="search" />
      <el-input v-model="filters.q" placeholder="词语、主题、来源文章" clearable @keyup.enter="search" @clear="search" />
      <el-select v-model="filters.kind" clearable placeholder="全部类型" @change="search"><el-option v-for="(name, key) in kinds" :key="key" :label="name" :value="key" /></el-select>
      <el-select v-model="filters.status" clearable placeholder="全部审核状态" @change="search"><el-option v-for="(name, key) in statuses" :key="key" :label="name" :value="key" /></el-select>
      <el-button @click="search">查询</el-button>
    </div>
    <div class="toolbar">
      <el-date-picker v-model="collectDate" type="date" value-format="YYYY-MM-DD" placeholder="选择采集日期" />
      <el-button type="primary" :loading="collecting" :disabled="!canWrite || activeJob" @click="collect">联合采集三类素材</el-button>
      <span class="muted">金句、词汇和申论素材共享正文与一次联合分析；已审核结论不会被覆盖</span>
      <el-button :disabled="!canWrite || !selected.length" @click="openReview('approved')">批量采用（{{ selected.length }}）</el-button>
      <el-button :disabled="!canWrite || !selected.length" @click="openReview('rejected')">批量不采用</el-button>
      <el-button @click="exportCurrent">导出当前页</el-button>
    </div>
    <el-collapse v-if="jobs.length" class="jobs">
      <el-collapse-item title="最近采集任务（运行中每5秒刷新）" name="jobs">
        <div v-for="job in jobs" :key="job.id" class="job-row">
          <strong>{{ job.issueDate }}</strong> · {{ jobStatuses[job.status] || job.status }} · 重试{{ job.attempts }}次 · {{ job.progress.pages || 0 }}版 / {{ job.progress.articles || 0 }}篇 · 已分析{{ job.progress.processed || 0 }}篇（缓存复用{{ job.progress.analysisCacheHits || 0 }}篇）
          <div class="muted">词汇：新增{{ job.progress.added || 0 }} / 重复{{ job.progress.duplicates || 0 }} / 拦截{{ job.progress.invalid || 0 }}；申论：新增{{ job.progress.shenlunAdded || 0 }} / 重复{{ job.progress.shenlunDuplicates || 0 }} / 质量未达标{{ job.progress.shenlunQualityRejected || 0 }} / 校验拦截{{ job.progress.shenlunInvalid || 0 }}</div>
          <div v-if="job.error" class="error">{{ job.error }}</div>
          <div v-for="failure in job.progress.failures || []" :key="failure" class="error">{{ failure }}</div>
        </div>
      </el-collapse-item>
    </el-collapse>
    <el-table v-loading="loading" :data="items" row-key="id" @selection-change="onSelection">
      <el-table-column type="selection" width="45" />
      <el-table-column label="词语 / 类型" width="160"><template #default="{ row }"><strong>{{ row.phrase }}</strong><div class="muted">{{ kinds[row.kind] }}</div></template></el-table-column>
      <el-table-column label="释义与应用" min-width="290"><template #default="{ row }"><div>{{ row.meaning }}</div><div class="muted">主题：{{ row.topics.join('、') }}</div><div class="muted">场景：{{ row.useCases.join('、') }}</div><div class="example">仿写：{{ row.sample.replace(/^仿写[：:]|^（仿写）/, '') }}</div></template></el-table-column>
      <el-table-column label="来源" min-width="200"><template #default="{ row }"><div>{{ row.issueDate }} · {{ row.pageNo }}版 {{ row.pageName }}</div><el-link :href="row.sourceUrl" target="_blank" rel="noopener noreferrer" type="primary">{{ row.sourceTitle }}</el-link><div class="muted">{{ row.sources.length }}处来源</div></template></el-table-column>
      <el-table-column label="审核" width="100"><template #default="{ row }"><el-tag :type="row.reviewStatus === 'approved' ? 'success' : row.reviewStatus === 'rejected' ? 'danger' : 'info'">{{ statuses[row.reviewStatus] }}</el-tag></template></el-table-column>
      <el-table-column label="操作" width="180" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="detail = row">详情</el-button><el-button link type="success" :disabled="!canWrite" @click="openReview('approved', row)">采用</el-button><el-button link type="danger" :disabled="!canWrite" @click="openReview('rejected', row)">不采用</el-button></template></el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[20, 50, 100]" layout="total, sizes, prev, pager, next" @current-change="load" @size-change="search" />
    <el-drawer :model-value="!!detail" title="词汇素材 · 原文核对" size="600px" @close="detail = null">
      <template v-if="detail"><h2>{{ detail.phrase }} <el-tag>{{ kinds[detail.kind] }}</el-tag></h2><p>{{ detail.meaning }}</p><p>使用边界：{{ detail.usageNote || '结合题目材料和原文语境使用。' }}</p><p>原创仿写：{{ detail.sample }}</p><div v-for="source in detail.sources" :key="source.url" class="source"><el-link :href="source.url" target="_blank" rel="noopener noreferrer" type="primary">{{ source.pageNo }}版 {{ source.pageName }} · {{ source.title }}</el-link><blockquote>{{ source.exactContext }}</blockquote></div><el-button :disabled="!canWrite" @click="openEdit(detail)">编辑释义与应用</el-button><p>审核：{{ statuses[detail.reviewStatus] }} · {{ detail.reviewedBy }}</p><p>{{ detail.reviewNote }}</p><el-button :disabled="!canWrite" @click="openReview('pending', detail)">退回待审核</el-button></template>
    </el-drawer>
    <el-dialog v-model="reviewVisible" :title="`审核：${statuses[reviewStatus]}`" width="480px"><p>已选择 {{ reviewIds.length }} 条素材</p><el-input v-model="reviewNote" type="textarea" :rows="4" maxlength="2000" placeholder="填写采用依据或不采用原因" /><template #footer><el-button @click="reviewVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveReview">确认</el-button></template></el-dialog>
    <el-dialog v-model="editVisible" title="编辑词汇应用（保存后需重新审核）" width="600px">
      <el-form label-width="90px"><el-form-item label="类型"><el-select v-model="editForm.kind"><el-option v-for="(name,key) in kinds" :key="key" :label="name" :value="key" /></el-select></el-form-item><el-form-item label="释义"><el-input v-model="editForm.meaning" type="textarea" /></el-form-item><el-form-item label="主题"><el-input v-model="editForm.topics" placeholder="多个主题用顿号分隔" /></el-form-item><el-form-item label="使用场景"><el-input v-model="editForm.useCases" placeholder="多个场景用顿号分隔" /></el-form-item><el-form-item label="原创仿写"><el-input v-model="editForm.sample" type="textarea" :rows="3" /></el-form-item><el-form-item label="使用边界"><el-input v-model="editForm.usageNote" type="textarea" /></el-form-item></el-form>
      <template #footer><el-button @click="editVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button></template>
    </el-dialog>
    <el-dialog v-model="rulesVisible" title="采集与筛选规则" width="680px"><template v-if="rules"><p>版本 {{ rules.version }} · 全版面 · 不设数量下限</p><h3>筛选要求</h3><p v-for="s in rules.selection" :key="s">{{ s }}</p><h3>排除内容</h3><p>{{ rules.exclude.join('；') }}</p><h3>入库核对</h3><p v-for="s in rules.validation" :key="s">{{ s }}</p></template></el-dialog>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { listVocabulary, listVocabularyJobs, collectVocabulary, reviewVocabulary, editVocabulary, vocabularyRules, type VocabularyItem, type VocabularyJob } from '@/api/rmrbVocabulary'
const kinds: Record<string, string> = { idiom: '成语', expression: '固定表达', term: '重点词语 / 政策表达' }
const statuses: Record<string, string> = { pending: '待审核', approved: '已采用', rejected: '不采用' }
const jobStatuses: Record<string, string> = { pending: '排队中', running: '采集中', completed: '完成', partial: '部分完成', failed: '失败' }
const auth = useAuthStore()
const canWrite = computed(() => auth.hasPermission('rmrb:write'))
const today = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai' }).format(new Date())
const filters = reactive({ issue_date: '', q: '', kind: '', status: '' })
const collectDate = ref(today), page = ref(1), pageSize = ref(20), total = ref(0)
const items = ref<VocabularyItem[]>([]), jobs = ref<VocabularyJob[]>([]), selected = ref<VocabularyItem[]>([]), detail = ref<VocabularyItem | null>(null)
const loading = ref(false), collecting = ref(false), saving = ref(false), reviewVisible = ref(false), rulesVisible = ref(false)
const rules = ref<Awaited<ReturnType<typeof vocabularyRules>> | null>(null)
const reviewIds = ref<string[]>([]), reviewStatus = ref('approved'), reviewNote = ref('')
const activeJob = computed(() => jobs.value.some(j => j.issueDate === collectDate.value && ['pending', 'running'].includes(j.status)))
const error = (e: unknown) => ElMessage.error(e instanceof Error ? e.message : '操作失败')
async function load() { loading.value = true; try { const result = await listVocabulary({ ...filters, issue_date: filters.issue_date || undefined, page: page.value, page_size: pageSize.value }); items.value = result.items; total.value = result.total; selected.value = [] } catch (e) { error(e) } finally { loading.value = false } }
async function refresh() { await load(); try { jobs.value = await listVocabularyJobs() } catch (e) { error(e) } }
function search() { page.value = 1; void load() }
function onSelection(rows: VocabularyItem[]) { selected.value = rows }
async function collect() { if (!collectDate.value) return; collecting.value = true; try { await collectVocabulary(collectDate.value); ElMessage.success('采集任务已提交，可在最近采集任务中查看进度'); await refresh() } catch (e) { error(e) } finally { collecting.value = false } }
function openReview(status: string, row?: VocabularyItem) { reviewIds.value = row ? [row.id] : selected.value.map(x => x.id); reviewStatus.value = status; reviewNote.value = row?.reviewNote || ''; reviewVisible.value = true }
async function saveReview() { saving.value = true; try { await reviewVocabulary(reviewIds.value, reviewStatus.value, reviewNote.value); reviewVisible.value = false; detail.value = null; ElMessage.success('审核已保存'); await load() } catch (e) { error(e) } finally { saving.value = false } }
function exportCurrent() { const blob = new Blob([JSON.stringify(items.value, null, 2)], { type: 'application/json' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `人民日报词汇-${filters.issue_date || today}-第${page.value}页.json`; a.click(); URL.revokeObjectURL(url) }
const editVisible = ref(false), editId = ref('')
const editForm = reactive({ kind: 'term', meaning: '', topics: '', useCases: '', sample: '', usageNote: '' })
function openEdit(row: VocabularyItem) { editId.value = row.id; Object.assign(editForm, { kind: row.kind, meaning: row.meaning, topics: row.topics.join('、'), useCases: row.useCases.join('、'), sample: row.sample, usageNote: row.usageNote || '' }); editVisible.value = true }
async function saveEdit() { saving.value = true; try { await editVocabulary(editId.value, { ...editForm, topics: editForm.topics.split(/[、，,]/).map(s => s.trim()).filter(Boolean), useCases: editForm.useCases.split(/[、，,]/).map(s => s.trim()).filter(Boolean) }); editVisible.value = false; detail.value = null; ElMessage.success('已保存，需重新审核'); await load() } catch (e) { error(e) } finally { saving.value = false } }
let timer: ReturnType<typeof setInterval> | undefined
onMounted(async () => { await refresh(); try { rules.value = await vocabularyRules() } catch (e) { error(e) }; timer = setInterval(async () => { if (jobs.value.some(j => ['pending', 'running'].includes(j.status))) await refresh() }, 5000) })
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>
<style scoped>
.vocabulary-page { padding: 20px; color: var(--el-text-color-primary); }
.toolbar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }
.toolbar h2 { margin: 0; margin-right: auto; }
.filters { margin-top: 16px; }
.filters .el-input { width: 230px; }
.filters .el-select { width: 180px; }
.muted { color: var(--el-text-color-secondary); font-size: 12px; margin-top: 5px; }
.example { background: var(--el-fill-color-light); padding: 8px; margin-top: 8px; }
.jobs, .el-pagination { margin: 16px 0; }
.job-row, .source { padding: 12px 0; border-bottom: 1px solid var(--el-border-color-lighter); }
.error { color: var(--el-color-danger); }
blockquote { margin: 12px 0; padding: 12px; background: var(--el-fill-color-light); line-height: 1.8; white-space: pre-wrap; }
</style>
