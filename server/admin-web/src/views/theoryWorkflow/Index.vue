<template>
  <div class="workflow-page">
    <el-card shadow="never">
      <div class="toolbar">
        <div><h2>时政出题工作台</h2><p>采集人民日报候选文章，审核选题后生成套题；全部题目审核通过后发布到时政要点。</p></div>
        <div class="collect"><el-date-picker v-model="issueDate" type="date" value-format="YYYY-MM-DD" placeholder="选择刊期" /><el-button type="primary" :loading="collecting" @click="collect">采集刊期</el-button></div>
      </div>
    </el-card>
    <el-card v-if="collections.length" shadow="never" class="collection-card">
      <template #header><div class="toolbar"><b>最近采集任务</b><el-button link @click="loadCollections">刷新任务</el-button></div></template>
      <div v-for="job in collections.slice(0, 4)" :key="job.id" class="collection-row"><span>{{ job.issueDate }}</span><el-tag size="small" :type="collectionTag(job.status)">{{ collectionLabel(job.status) }}</el-tag><span>发现 {{ job.discovered }} 篇</span><span>新增 {{ job.created }} 篇</span><span v-if="job.failedPages || job.failedSources" class="warning">失败 {{ job.failedPages + job.failedSources }}</span><span v-if="job.error" class="warning">{{ job.error }}</span></div>
    </el-card>
    <el-card shadow="never">
      <div class="filters">
        <el-date-picker v-model="filterDate" type="date" value-format="YYYY-MM-DD" clearable placeholder="全部刊期" @change="load" />
        <el-select v-model="filterStatus" clearable placeholder="全部审核状态" @change="load"><el-option label="待审核" value="pending"/><el-option label="已通过" value="approved"/><el-option label="已忽略" value="rejected"/></el-select>
        <el-button @click="load">刷新</el-button><span class="muted">共 {{ total }} 篇 · 自动采集每天06:30</span>
      </div>
      <el-table v-loading="loading" :data="items" row-key="id" empty-text="暂无候选文章，请先采集刊期">
        <el-table-column prop="date" label="刊期" width="112" />
        <el-table-column label="文章" min-width="280"><template #default="{ row }"><div class="title">{{ row.title }}</div><div class="muted">{{ row.pageNo }}版 {{ row.pageName }}</div></template></el-table-column>
        <el-table-column label="选题信号" width="135"><template #default="{ row }"><el-tooltip :content="row.reasons.join('；') || '自动初筛参考分，需人工判断'"><el-tag :type="row.signal === 'S1' ? 'danger' : row.signal === 'S2' ? 'warning' : 'info'">{{ row.signal }} · {{ row.valueScore }}分</el-tag></el-tooltip></template></el-table-column>
        <el-table-column label="审核" width="110"><template #default="{ row }"><el-tag :type="sourceTag(row.reviewStatus)">{{ sourceLabel(row.reviewStatus) }}</el-tag></template></el-table-column>
        <el-table-column label="套题版本" min-width="210"><template #default="{ row }"><div v-for="item in row.papers" :key="item.id" class="paper-row"><el-link type="primary" @click="openPaper(item.id)">{{ item.title }} v{{ item.version }}</el-link><el-tag size="small" :type="paperTag(item.status)">{{ paperLabel(item.status) }}</el-tag><span class="muted">{{ item.questionCount }}题</span></div><span v-if="!row.papers.length" class="muted">尚未生成</span></template></el-table-column>
        <el-table-column label="操作" width="255" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="openSource(row)">原文</el-button><el-button v-if="row.reviewStatus !== 'approved'" link type="success" @click="reviewSource(row,'approved')">通过</el-button><el-button v-if="row.reviewStatus !== 'rejected'" link type="info" @click="reviewSource(row,'rejected')">忽略</el-button><el-button v-if="row.reviewStatus === 'approved'" link type="primary" @click="startGeneration(row)">生成套题</el-button></template></el-table-column>
      </el-table>
      <div class="pagination"><el-pagination v-model:current-page="page" :page-size="30" :total="total" layout="prev, pager, next" @current-change="load" /></div>
    </el-card>
    <el-drawer v-model="sourceOpen" :title="sourceDetail?.displayTitle || '文章原文'" size="60%">
      <div class="source-link" v-if="sourceDetail?.primarySourceUrl"><el-link :href="sourceDetail.primarySourceUrl" target="_blank">打开来源网页</el-link></div>
      <pre class="source-body">{{ sourceDetail?.bodyText || '档案中暂时没有全文，生成时系统会尝试从原文链接采集并保存快照。' }}</pre>
    </el-drawer>
    <el-drawer v-model="paperOpen" :title="paper?.title || '套题审核'" size="78%" destroy-on-close>
      <template v-if="paper">
        <el-alert v-if="paper.error" type="error" :title="paper.error" show-icon />
        <el-alert v-if="paper.report?.errors?.length" type="warning" title="质检发现问题" :description="paper.report.errors.join('；')" show-icon />
        <div class="paper-summary"><el-tag :type="paperTag(paper.status)">{{ paperLabel(paper.status) }}</el-tag><span>{{ paper.questionCount }} 道有效题 / 20</span><span>已审 {{ paper.approvedCount }}</span><span v-if="paper.report?.typeCounts">题型 直 {{ paper.report.typeCounts.direct || 0 }} / 组 {{ paper.report.typeCounts.combo || 0 }} / 计 {{ paper.report.typeCounts.count || 0 }}</span><span v-if="paper.report?.answerDistribution">答案 A/B/C/D {{ paper.report.answerDistribution.A || 0 }}/{{ paper.report.answerDistribution.B || 0 }}/{{ paper.report.answerDistribution.C || 0 }}/{{ paper.report.answerDistribution.D || 0 }}</span><span v-if="paper.report?.distractorTrickCounts">干扰手法 {{ trickKindsUsed() }}/5 种</span><span v-if="paper.report?.focusTypeCounts">考点核心 {{ paper.report.focusTypeCounts.core || 0 }} · 指标 {{ paper.report.focusTypeCounts.metric || 0 }} · 部署 {{ paper.report.focusTypeCounts.deployment || 0 }}</span><span>规则 {{ paper.rulesVersion }}</span><el-button type="primary" :disabled="paper.status !== 'review' || paper.approvedCount !== 20" @click="publish">发布到时政要点</el-button></div>
        <el-alert v-if="paper.report?.rubricSources?.length" type="info" :closable="false" :title="`命题与审核依据：${paper.report.rubricSources.join('；')}`" />
        <el-empty v-if="!paper.questions?.length" description="生成任务尚未完成或无有效题目，完成后刷新查看" />
        <el-card v-for="(q, index) in paper.questions" :key="index" shadow="never" class="question-card">
          <template #header><div class="q-head"><b>第 {{ index + 1 }} 题</b><el-tag size="small">{{ subtypeName(q.subtype) }}</el-tag><el-tag size="small" type="info">{{ focusTypeName(q.focusType) }}{{ q.numericRecall ? ' · 数值记忆' : '' }}</el-tag><el-tag size="small" :type="q.reviewStatus==='approved'?'success':q.reviewStatus==='rejected'?'danger':'warning'">{{ q.reviewStatus==='approved'?'已通过':q.reviewStatus==='rejected'?'已驳回':'待审核' }}</el-tag><span class="muted">{{ q.topic }}</span><span class="spacer"/><el-button size="small" @click="saveReview(index,'pending')">保存为待审</el-button><el-button size="small" type="success" @click="saveReview(index,'approved')">通过</el-button><el-button size="small" type="danger" plain @click="saveReview(index,'rejected')">驳回</el-button></div></template>
          <el-input v-model="q.stem" type="textarea" :rows="3" placeholder="题干" />
          <div class="options"><el-input v-for="(option, oi) in q.options" :key="oi" v-model="q.options[oi]" :placeholder="`选项${'ABCD'[oi]}`"><template #prepend>{{ 'ABCD'[oi] }}</template></el-input></div>
          <div class="edit-grid"><el-select v-model="q.answer"><el-option v-for="letter in ['A','B','C','D']" :key="letter" :label="letter" :value="letter" /></el-select><el-input v-model="q.topic" placeholder="考点"/><el-input v-model="q.tag" placeholder="细分标签"/><el-input v-model="q.reviewNote" placeholder="审核意见"/></div>
          <el-input v-model="q.analysis" type="textarea" :rows="3" placeholder="解析" class="field-gap" />
          <el-input v-model="q.sourceSentence" type="textarea" :rows="2" placeholder="原文依据" class="field-gap" />
          <el-input v-model="q.sourceRef" placeholder="原文出处锚点（如：第一部分·总体要求段）" class="field-gap" />
          <div class="quality-meta"><span>自动难度：{{ q.difficulty || '待计算' }}/5</span><span>干扰项手法 JSON（逐个错项标注）：</span></div>
          <el-input v-model="distractorEditors[index]" type="textarea" :rows="3" class="field-gap" />
          <el-collapse v-if="paper.reviewHistory.some((entry) => entry.questionIndex === index)" class="field-gap"><el-collapse-item title="审核与修改记录"><div v-for="(entry, hi) in paper.reviewHistory.filter((event) => event.questionIndex === index)" :key="hi" class="history-row"><span>{{ entry.at }} · {{ entry.reviewer }}</span><el-tag size="small">{{ entry.status }}</el-tag><span>{{ changeSummary(entry) }}</span><span>{{ entry.note }}</span></div></el-collapse-item></el-collapse>
        </el-card>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { collectTheorySources, fetchTheoryCollections, fetchTheoryPaper, fetchTheorySource, fetchTheorySources, generateTheoryPaper, publishTheoryPaper, reviewTheorySource, saveTheoryQuestionReview } from '@/api/theoryWorkflow'
import type { TheoryCollection, TheoryPaper, TheoryQuestion, TheoryQuestionReviewEvent, TheorySource } from '@/api/theoryWorkflow'

const issueDate = ref(new Date().toLocaleDateString('sv-SE'))
const filterDate = ref('')
const filterStatus = ref('')
const items = ref<TheorySource[]>([])
const collections = ref<TheoryCollection[]>([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const collecting = ref(false)
const sourceOpen = ref(false)
const sourceDetail = ref<{bodyText?: string; displayTitle: string; primarySourceUrl: string} | null>(null)
const paperOpen = ref(false)
const paper = ref<(TheoryPaper & {questions: TheoryQuestion[]; reviewHistory: TheoryQuestionReviewEvent[]}) | null>(null)
const distractorEditors = ref<Record<number, string>>({})
let poller: ReturnType<typeof setInterval> | undefined
let collectionPoller: ReturnType<typeof setInterval> | undefined

async function load() { loading.value = true; try { const data = await fetchTheorySources({ issue_date: filterDate.value || undefined, status: filterStatus.value || undefined, page: page.value, page_size: 30 }); items.value = data.items; total.value = data.total } catch (error) { ElMessage.error(error instanceof Error ? error.message : '文章列表加载失败') } finally { loading.value = false } }
async function collect() { if (!issueDate.value) return; collecting.value = true; try { await collectTheorySources(issueDate.value); ElMessage.success('采集任务已提交，可在任务列表查看进度'); filterDate.value = issueDate.value; await Promise.all([load(), loadCollections()]) } catch (error) { ElMessage.error(error instanceof Error ? error.message : '采集失败') } finally { collecting.value = false } }
async function loadCollections() { try { const next = await fetchTheoryCollections(); const previous = new Map(collections.value.map((job) => [job.id, job.status])); const finished = next.some((job) => ['completed','failed','waiting_for_source'].includes(job.status) && ['queued','running'].includes(previous.get(job.id) || '')); collections.value = next; if (finished) void load() } catch { /* 文章列表仍可使用 */ } }
async function openSource(row: TheorySource) { sourceOpen.value = true; sourceDetail.value = null; try { sourceDetail.value = await fetchTheorySource(row.id) } catch (error) { ElMessage.error(error instanceof Error ? error.message : '原文读取失败') } }
async function reviewSource(row: TheorySource, status: string) { try { const note = status === 'rejected' ? (await ElMessageBox.prompt('记录忽略原因（可留空）', '忽略候选', { inputValue: row.reviewNote })).value : ''; await reviewTheorySource(row.id, status, note); ElMessage.success(status === 'approved' ? '文章已通过选用审核' : '候选已忽略'); await load() } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(error instanceof Error ? error.message : '审核失败') } }
async function startGeneration(row: TheorySource) { try { const { value } = await ElMessageBox.prompt('套题标题', '生成20题套题', { inputValue: `${row.title} · 时政模拟题` }); const created = await generateTheoryPaper(row.id, value); ElMessage.success(`第${created.version}版生成任务已提交`); await load() } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(error instanceof Error ? error.message : '提交失败') } }
async function openPaper(id: string) { paperOpen.value = true; paper.value = null; await refreshPaper(id); if (poller) clearInterval(poller); poller = setInterval(() => { if (paper.value && ['queued','generating'].includes(paper.value.status)) void refreshPaper(id) }, 5000) }
async function refreshPaper(id: string) { try { paper.value = await fetchTheoryPaper(id); distractorEditors.value = Object.fromEntries((paper.value.questions || []).map((q, index) => [index, JSON.stringify(q.distractors || {}, null, 2)])) } catch (error) { ElMessage.error(error instanceof Error ? error.message : '套题加载失败') } }
async function saveReview(index: number, status: TheoryQuestion['reviewStatus']) { if (!paper.value) return; try { const distractors = JSON.parse(distractorEditors.value[index] || '{}'); if (!distractors || typeof distractors !== 'object' || Array.isArray(distractors)) throw new Error('干扰项标注必须是 JSON 对象'); await saveTheoryQuestionReview(paper.value.id, index, {...paper.value.questions[index], distractors, reviewStatus: status}); await refreshPaper(paper.value.id); ElMessage.success(status === 'approved' ? '题目已通过' : status === 'rejected' ? '题目已驳回' : '题目已保存为待审') } catch (error) { await refreshPaper(paper.value.id); ElMessage.error(error instanceof Error ? error.message : '质检未通过，请检查题目与原文依据') } }
async function publish() { if (!paper.value) return; try { await ElMessageBox.confirm('发布后会创建新的时政要点版本，当前在线版本将停止新入口展示。', '确认发布'); await publishTheoryPaper(paper.value.id); ElMessage.success('套题已发布'); await refreshPaper(paper.value.id); await load() } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(error instanceof Error ? error.message : '发布失败') } }
function sourceTag(status: string) { return status === 'approved' ? 'success' : status === 'rejected' ? 'info' : 'warning' }
function sourceLabel(status: string) { return status === 'approved' ? '已通过' : status === 'rejected' ? '已忽略' : '待审核' }
function paperTag(status: string) { return status === 'published' ? 'success' : status === 'failed' || status === 'needs_revision' ? 'danger' : status === 'review' ? 'warning' : 'info' }
function paperLabel(status: string) { return ({queued:'排队中',generating:'生成中',review:'待审题',needs_revision:'需修订',failed:'生成失败',published:'已上线',superseded:'已被新版本替代'} as Record<string,string>)[status] || status }
function subtypeName(value: string) { return ({direct:'直接判断',combo:'组合题',count:'计数题'} as Record<string,string>)[value] || value }
function focusTypeName(value: string) { return ({general:'总论',core:'核心提法',metric:'关键指标',deployment:'其他部署',background:'保障背景'} as Record<string,string>)[value] || value }
function collectionTag(status: string) { return status === 'completed' ? 'success' : status === 'failed' ? 'danger' : 'warning' }
function collectionLabel(status: string) { return ({queued:'排队中',running:'采集中',completed:'已完成',failed:'失败',waiting_for_source:'等待来源开放'} as Record<string,string>)[status] || status }
function changeSummary(event: TheoryQuestionReviewEvent) { const labels: Record<string,string> = { stem: '题干', options: '选项', answer: '答案', analysis: '解析', sourceSentence: '原文依据', sourceRef: '出处锚点', topic: '考点', tag: '考点标签', distractors: '干扰项手法', reviewStatus: '审核状态' }; const changed = Object.keys(labels).filter((key) => JSON.stringify(event.before?.[key]) !== JSON.stringify(event.after?.[key])).map((key) => labels[key]); return changed.length ? `修改：${changed.join('、')}` : '审核状态更新' }
function trickKindsUsed() { return Object.values(paper.value?.report?.distractorTrickCounts || {}).filter((count) => count > 0).length }
onMounted(() => { void load(); void loadCollections(); collectionPoller = setInterval(() => { void loadCollections() }, 10000) })
onBeforeUnmount(() => { if (poller) clearInterval(poller); if (collectionPoller) clearInterval(collectionPoller) })
</script>

<style scoped>
.workflow-page{display:flex;flex-direction:column;gap:16px}.toolbar,.filters,.paper-summary,.q-head{display:flex;align-items:center;gap:12px}.toolbar{justify-content:space-between}h2{margin:0 0 8px;font-size:20px}p{margin:0;color:#777}.collect{display:flex;gap:8px}.filters{margin-bottom:14px}.muted{color:#909399;font-size:12px}.title{font-weight:600}.paper-row{display:flex;align-items:center;gap:8px;margin:4px 0}.pagination{display:flex;justify-content:flex-end;margin-top:16px}.source-body{white-space:pre-wrap;word-break:break-word;line-height:1.8;font:14px/1.8 sans-serif}.source-link{margin-bottom:12px}.paper-summary{margin:16px 0;flex-wrap:wrap}.question-card{margin-bottom:14px}.q-head{width:100%}.spacer{flex:1}.options{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}.edit-grid{display:grid;grid-template-columns:140px 1fr 1fr 1fr;gap:8px;margin-top:10px}.quality-meta{display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin-top:10px;color:#606266;font-size:12px}.field-gap{margin-top:10px}.collection-row{display:flex;align-items:center;gap:14px;padding:6px 0;border-bottom:1px solid #ebeef5}.history-row{display:flex;align-items:center;gap:10px;padding:5px 0;color:#606266;font-size:12px}.warning{color:#e6a23c;font-size:12px}@media(max-width:800px){.toolbar{align-items:flex-start;flex-direction:column}.options{grid-template-columns:1fr}.edit-grid{grid-template-columns:1fr}.collection-row{align-items:flex-start;flex-wrap:wrap}}
</style>
