<template>
  <div class="page">
    <div class="toolbar">
      <div><h2>客户端评论 / 金句</h2><p>来源：人民日报客户端评论页；按文章明确发布日期筛选最近 48 小时。AI 提取结果需人工核对原文后审核。</p></div>
      <div class="actions">
        <el-button type="primary" :loading="collecting" @click="collect">采集最近 48 小时文章</el-button>
        <el-button @click="load">刷新</el-button>
      </div>
    </div>
    <el-alert type="info" :closable="false" show-icon title="每行先在“文章审核”列点击“确认为评论”；确认后该行的金句管理才可点击。排除文章会删除其金句，并按可识别的标题系列前缀自动过滤后续同类文章。" />
    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column prop="issueDate" label="发布日期" width="112" />
      <el-table-column label="文章" min-width="320"><template #default="{ row }"><strong>{{ row.title }}</strong><div class="muted">{{ row.subtitle || row.columnLabel || row.inclusionReason }}</div></template></el-table-column>
      <el-table-column prop="author" label="作者" width="140" />
      <el-table-column label="文章审核" width="225"><template #default="{ row }">
        <template v-if="row.articleReviewStatus === 'pending'"><el-button link type="success" @click="reviewArticle(row, 'approved')">确认为评论</el-button><el-button link type="danger" @click="reviewArticle(row, 'excluded')">非评论，排除</el-button></template>
        <el-tag v-else :type="row.articleReviewStatus === 'approved' ? 'success' : 'info'">{{ row.articleReviewStatus === 'approved' ? '已确认为评论' : '已排除' }}</el-tag>
      </template></el-table-column>
      <el-table-column label="采集/原文" width="130"><template #default="{ row }"><el-tag :type="row.originalMdKey ? 'success' : 'warning'">{{ row.originalMdKey ? '原文已整理' : row.workflowStatus }}</el-tag></template></el-table-column>
      <el-table-column label="三刀解剖" width="120"><template #default="{ row }">{{ analysisLabel(row.analysisStatus) }}</template></el-table-column>
      <el-table-column label="金句" width="100"><template #default="{ row }">{{ quoteCounts[row.id] ?? '—' }} 条</template></el-table-column>
      <el-table-column label="操作" width="280" fixed="right"><template #default="{ row }">
        <el-button link type="primary" @click="openSource(row)">原文</el-button>
        <el-button link type="primary" :disabled="!row.analysisHtmlKey" @click="viewAnalysis(row)">三刀预览</el-button>
        <el-button v-if="row.articleReviewStatus === 'approved'" link type="success" @click="openQuotes(row)">金句管理</el-button>
        <el-tooltip v-else content="请先在本行“文章审核”列确认这是评论文章" placement="top">
          <span><el-button link type="info" disabled>先审核文章</el-button></span>
        </el-tooltip>
      </template></el-table-column>
    </el-table>
    <el-pagination v-if="total > 0" v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[10, 20, 50, 100]" :total="total" layout="total, sizes, prev, pager, next, jumper" @current-change="load" @size-change="handleSizeChange" />
    <el-empty v-if="!loading && items.length === 0" description="最近 48 小时暂无已采集的客户端评论；点击上方按钮采集" />

    <el-dialog v-model="quoteVisible" :title="`${current?.title || ''}｜金句管理`" width="min(1100px, 96vw)" top="4vh" destroy-on-close>
      <div class="quote-toolbar">
        <el-button type="primary" :loading="aiCollecting" @click="collectAi">采集金句候选</el-button>
        <el-button type="success" @click="startManual">人工新增</el-button>
        <a v-if="current?.sourceUrl" :href="current.sourceUrl" target="_blank" rel="noopener noreferrer">打开来源文章</a>
      </div>
      <el-alert class="quote-hint" type="info" :closable="false" title="优先采集原文网页加粗标注的完整句；无加粗标注时由 AI 从完整句中筛选候选。候选保留原文全文，均需人工审核。" />
      <el-empty v-if="quotes.length === 0 && !editing" description="暂无金句。可用 AI 初筛，也可直接人工摘录。" />
      <div v-for="quote in quotes" :key="quote.id" class="quote-card">
        <div class="quote-head"><el-tag size="small" :type="quote.collectionMethod === 'bold' ? 'success' : quote.collectionMethod === 'ai' ? 'warning' : 'primary'">{{ quote.collectionMethod === 'bold' ? '原文加粗' : quote.collectionMethod === 'ai' ? 'AI 筛选' : '人工采集' }}</el-tag><el-tag size="small" :type="quote.reviewStatus === 'approved' ? 'success' : quote.reviewStatus === 'rejected' ? 'danger' : 'info'">{{ reviewLabel(quote.reviewStatus) }}</el-tag><span class="quote-type">{{ quote.quoteType }}</span></div>
        <blockquote>{{ quote.text }}</blockquote>
        <div class="tags">主题：{{ quote.topics.join('、') || '待补充' }}　｜　场景：{{ quote.useCases.join('、') || '待补充' }}</div>
        <p v-if="quote.applicationExample" class="example">{{ quote.applicationExample }}</p>
        <div class="quote-actions"><el-button link type="success" :disabled="quote.reviewStatus === 'approved'" @click="reviewQuote(quote, 'approved')">核对原文并通过</el-button><el-button link type="warning" @click="reviewQuote(quote, 'changes_requested')">需修改</el-button><el-button link type="danger" @click="reviewQuote(quote, 'rejected')">不采用</el-button><el-button v-if="quote.collectionMethod === 'manual'" link type="primary" @click="editQuote(quote)">编辑</el-button><el-button link type="danger" @click="removeQuote(quote)">删除</el-button></div>
      </div>
      <el-form v-if="editing" label-width="90px" class="quote-form">
        <el-form-item label="金句原文"><el-input v-model="draft.text" type="textarea" :rows="4" placeholder="请逐字摘录完整句子；保存时会校验来源原文" /></el-form-item>
        <el-form-item label="类型"><el-select v-model="draft.quoteType"><el-option v-for="type in quoteTypes" :key="type" :label="type" :value="type" /></el-select></el-form-item>
        <el-form-item label="主题标签"><el-input v-model="draft.topicsText" placeholder="用顿号分隔，如基层治理、为民服务" /></el-form-item>
        <el-form-item label="适用场景"><el-input v-model="draft.useCasesText" placeholder="用顿号分隔，如分论点论证、结尾升华" /></el-form-item>
        <el-form-item label="申论仿写"><el-input v-model="draft.applicationExample" type="textarea" :rows="3" placeholder="标明仿写，不要伪装成原文" /></el-form-item>
        <div class="form-actions"><el-button @click="editing = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveQuote">保存待审核</el-button></div>
      </el-form>
    </el-dialog>
    <el-dialog v-model="previewVisible" :title="previewTitle" width="min(1080px, 94vw)" top="4vh"><iframe class="preview" :srcdoc="previewHtml" sandbox="" /></el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { collectAiRmrbCommentQuotes, collectPeopleappOpinionComments, createRmrbCommentQuote, deleteRmrbCommentQuote, getRmrbCommentArtifact, listPeopleappOpinionComments, listRmrbCommentQuotes, reviewPeopleappOpinionArticle, reviewRmrbCommentQuote, updateRmrbCommentQuote, type RmrbCommentItem, type RmrbCommentQuote } from '@/api/rmrbComments'

const items = ref<RmrbCommentItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const quoteCounts = ref<Record<string, number>>({})
const loading = ref(false)
const collecting = ref(false)
const aiCollecting = ref(false)
const saving = ref(false)
const quoteVisible = ref(false)
const previewVisible = ref(false)
const previewTitle = ref('')
const previewHtml = ref('')
const current = ref<RmrbCommentItem | null>(null)
const quotes = ref<RmrbCommentQuote[]>([])
const editing = ref(false)
const editingId = ref('')
const quoteTypes = ['立意', '论证', '对策', '过渡', '收束', '表达']
const draft = ref({ text: '', quoteType: '论证', topicsText: '', useCasesText: '', applicationExample: '' })

async function load() {
  loading.value = true
  try {
    const result = await listPeopleappOpinionComments(page.value, pageSize.value)
    items.value = result.items
    total.value = result.total
    await Promise.all(items.value.map(async row => { try { quoteCounts.value[row.id] = (await listRmrbCommentQuotes(row.id)).length } catch { quoteCounts.value[row.id] = 0 } }))
  } catch (error) { ElMessage.error(String(error)) } finally { loading.value = false }
}
function handleSizeChange() { page.value = 1; load() }
async function collect() {
  collecting.value = true
  try {
    const result = await collectPeopleappOpinionComments()
    page.value = 1
    ElMessage.success(`最近 48 小时发现 ${result.discovered} 篇，新增 ${result.created} 篇；原文整理和三刀分析已后台处理`)
    await load()
    window.setTimeout(load, 2500)
    window.setTimeout(load, 7000)
  } catch (error) { ElMessage.error(String(error)) } finally { collecting.value = false }
}
function openSource(row: RmrbCommentItem) { if (row.sourceUrl) window.open(row.sourceUrl, '_blank', 'noopener,noreferrer') }
async function viewAnalysis(row: RmrbCommentItem) { try { previewHtml.value = await getRmrbCommentArtifact(row.id, 'analysis_html'); previewTitle.value = `${row.title}｜三刀解剖`; previewVisible.value = true } catch (error) { ElMessage.error(String(error)) } }
async function openQuotes(row: RmrbCommentItem) { current.value = row; quoteVisible.value = true; editing.value = false; await refreshQuotes() }
async function reviewArticle(row: RmrbCommentItem, decision: 'approved' | 'excluded') {
  if (decision === 'excluded') {
    try { await ElMessageBox.confirm('排除后将删除该文章下的金句；若标题带有明确栏目/系列前缀，后续同前缀文章也会自动过滤。确认继续？', '排除非评论文章', { type: 'warning', confirmButtonText: '排除文章', cancelButtonText: '取消' }) } catch { return }
  }
  try {
    const result = await reviewPeopleappOpinionArticle(row.id, decision, decision === 'excluded' ? '人工判定不属于申论评论文章' : '')
    if (decision === 'excluded') {
      const ruleText = result.exclusionTitlePrefix ? `；已建立“${result.exclusionTitlePrefix}”标题前缀过滤规则，另过滤 ${result.filteredArticles} 篇` : '；未识别到稳定标题前缀，仅排除此篇'
      ElMessage.success(`文章已排除，删除 ${result.deletedQuotes} 条金句${ruleText}`)
    } else {
      ElMessage.success('文章已确认属于评论文章，现在可以审核金句')
    }
    await load()
  } catch (error) { ElMessage.error(String(error)) }
}
async function refreshQuotes() { if (!current.value) return; try { quotes.value = await listRmrbCommentQuotes(current.value.id); quoteCounts.value[current.value.id] = quotes.value.length } catch (error) { ElMessage.error(String(error)) } }
async function collectAi() { if (!current.value) return; aiCollecting.value = true; try { const added = await collectAiRmrbCommentQuotes(current.value.id); const boldCount = added.filter(item => item.collectionMethod === 'bold').length; const aiCount = added.length - boldCount; ElMessage.success(`新增 ${added.length} 条完整句候选（原文加粗 ${boldCount} 条，AI 筛选 ${aiCount} 条），请核对原文并审核`); await refreshQuotes() } catch (error) { ElMessage.error(String(error)) } finally { aiCollecting.value = false } }
function startManual() { editingId.value = ''; draft.value = { text: '', quoteType: '论证', topicsText: '', useCasesText: '', applicationExample: '' }; editing.value = true }
function editQuote(row: RmrbCommentQuote) { editingId.value = row.id; draft.value = { text: row.text, quoteType: row.quoteType, topicsText: row.topics.join('、'), useCasesText: row.useCases.join('、'), applicationExample: row.applicationExample }; editing.value = true }
function quotePayload() { return { text: draft.value.text, quoteType: draft.value.quoteType, topics: draft.value.topicsText.split(/[、，,]/).map(x => x.trim()).filter(Boolean), useCases: draft.value.useCasesText.split(/[、，,]/).map(x => x.trim()).filter(Boolean), applicationExample: draft.value.applicationExample } }
async function saveQuote() { if (!current.value) return; saving.value = true; try { const payload = quotePayload(); if (editingId.value) await updateRmrbCommentQuote(editingId.value, payload); else await createRmrbCommentQuote(current.value.id, payload); editing.value = false; ElMessage.success('金句已保存，等待审核'); await refreshQuotes() } catch (error) { ElMessage.error(String(error)) } finally { saving.value = false } }
async function reviewQuote(row: RmrbCommentQuote, decision: string) { if (decision === 'rejected') { try { await ElMessageBox.confirm('不采用并删除这条金句？删除后刷新列表也不会再显示。', '删除金句', { type: 'warning', confirmButtonText: '不采用并删除', cancelButtonText: '取消' }) } catch { return } }; try { await reviewRmrbCommentQuote(row.id, { decision, note: '' }); ElMessage.success(decision === 'approved' ? '金句审核通过' : decision === 'rejected' ? '金句已删除' : '已标记为需修改'); await refreshQuotes() } catch (error) { ElMessage.error(String(error)) } }
async function removeQuote(row: RmrbCommentQuote) { try { await ElMessageBox.confirm('确认删除这条金句？', '删除金句', { type: 'warning' }); await deleteRmrbCommentQuote(row.id); await refreshQuotes() } catch { /* cancelled */ } }
function analysisLabel(value: string) { return ({ pending: '待生成', processing: '生成中', draft: '待审核', edited: '已编辑', failed: '失败' } as Record<string, string>)[value] || value }
function reviewLabel(value: string) { return ({ pending: '待审核', approved: '已通过', rejected: '不采用', changes_requested: '需修改' } as Record<string, string>)[value] || value }
onMounted(load)
</script>

<style scoped>
.page{padding:20px;display:flex;flex-direction:column;gap:16px}.toolbar{display:flex;align-items:center;justify-content:space-between;gap:16px}.toolbar h2{margin:0 0 6px}.toolbar p,.muted{color:#777;font-size:13px;margin:0}.actions,.quote-toolbar{display:flex;align-items:center;gap:12px}.quote-hint{margin-top:12px}.quote-card{padding:14px 4px;border-bottom:1px solid #eee}.quote-head,.quote-actions,.tags,.form-actions{display:flex;align-items:center;gap:10px}.quote-type,.tags{color:#666;font-size:13px}.quote-card blockquote{margin:12px 0;padding:12px 16px;background:#f8f8f8;border-left:3px solid #c33;line-height:1.9}.example{padding:8px 12px;background:#f3f7fb;color:#526477}.quote-actions{justify-content:flex-end}.quote-form{margin-top:20px;padding-top:16px;border-top:1px solid #eee}.form-actions{justify-content:flex-end}.preview{width:100%;height:78vh;border:1px solid #eee;border-radius:6px;background:#fff}@media(max-width:900px){.toolbar{align-items:flex-start;flex-direction:column}.actions{flex-wrap:wrap}.page{padding:12px}}
</style>
