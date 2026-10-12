<template>
  <div class="page">
    <div class="toolbar">
      <div><h2>评论文章</h2><p>从各版面识别明确评论栏目及高置信评论/社论体裁，生成申论原文和三刀解剖物料。</p></div>
      <div class="actions">
        <el-date-picker v-model="issueDate" type="date" value-format="YYYY-MM-DD" placeholder="选择刊期" />
        <el-button type="primary" :loading="scanning" @click="scan">扫描并整理原文</el-button>
        <el-button @click="load">刷新</el-button>
      </div>
    </div>
    <el-alert type="info" :closable="false" show-icon title="AI 解剖稿仅为待审草稿；必须人工检查原文引用、事实和申论适配后才能审核通过。" />
    <div class="filters">
      <el-input v-model="keyword" clearable placeholder="按文章标题搜索" @keyup.enter="load" />
      <el-select v-model="status" clearable placeholder="工作状态" @change="load">
        <el-option label="原文已整理" value="original_ready" /><el-option label="分析草稿" value="analysis_draft" />
        <el-option label="审核通过" value="approved" /><el-option label="处理失败" value="failed" />
      </el-select>
      <el-button @click="load">查询</el-button>
    </div>
    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column prop="issueDate" label="刊期" width="112" />
      <el-table-column label="文章" min-width="280">
        <template #default="{ row }"><strong>{{ row.title }}</strong><div class="muted">{{ row.subtitle || row.columnLabel || row.inclusionReason }}</div></template>
      </el-table-column>
      <el-table-column label="版面" width="150"><template #default="{ row }">{{ row.pageNo || '—' }} {{ row.pageName }}</template></el-table-column>
      <el-table-column prop="author" label="作者" width="130" />
      <el-table-column label="原文" width="100"><template #default="{ row }"><el-tag :type="row.originalMdKey ? 'success' : 'warning'">{{ row.originalMdKey ? '已整理' : row.workflowStatus }}</el-tag></template></el-table-column>
      <el-table-column label="三刀解剖" width="120"><template #default="{ row }"><el-tag :type="row.analysisStatus === 'draft' || row.analysisStatus === 'edited' ? 'warning' : 'info'">{{ analysisLabel(row.analysisStatus) }}</el-tag></template></el-table-column>
      <el-table-column label="审核" width="100"><template #default="{ row }"><el-tag :type="row.reviewStatus === 'approved' ? 'success' : 'info'">{{ reviewLabel(row.reviewStatus) }}</el-tag></template></el-table-column>
      <el-table-column label="操作" width="390" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" :disabled="!row.originalHtmlKey" @click="view(row, 'original_html')">原文预览</el-button>
          <el-button link type="primary" :disabled="!row.analysisHtmlKey" @click="view(row, 'analysis_html')">三刀预览</el-button>
          <el-dropdown @command="(kind: string) => view(row, kind)">
            <el-button link type="info">Markdown<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
            <template #dropdown><el-dropdown-menu><el-dropdown-item command="original_md">原文 Markdown</el-dropdown-item><el-dropdown-item command="analysis_md" :disabled="!row.analysisMdKey">三刀 Markdown</el-dropdown-item></el-dropdown-menu></template>
          </el-dropdown>
          <el-button link type="primary" :loading="generating === row.id" @click="analyze(row)">{{ row.analysisStatus === 'draft' ? '重新生成' : '生成三刀' }}</el-button>
          <el-button link type="success" :disabled="!row.analysisMdKey" @click="edit(row)">编辑/审核</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && items.length === 0" description="暂无评论文章；先选择刊期并扫描" />
    <el-dialog v-model="artifactVisible" :title="artifactTitle" width="min(1080px, 94vw)" top="4vh">
      <iframe v-if="artifactKind.endsWith('_html')" class="html-preview" :srcdoc="artifactText" sandbox="" :title="artifactTitle" />
      <pre v-else class="document">{{ artifactText }}</pre>
    </el-dialog>
    <el-dialog v-model="reviewVisible" title="编辑并审核三刀解剖" width="min(1000px, 94vw)" destroy-on-close>
      <div class="review-meta">{{ current?.title }} · {{ current?.issueDate }} · 来源依据：{{ current?.inclusionReason }}</div>
      <el-input v-model="draftMarkdown" type="textarea" :rows="24" placeholder="三刀解剖 Markdown" />
      <template #footer>
        <el-input v-model="reviewNote" class="review-note" placeholder="审核意见（可选）" />
        <el-button @click="saveReview('changes_requested')">退回修改</el-button><el-button type="danger" plain @click="saveReview('rejected')">不采用</el-button><el-button type="success" :loading="saving" @click="saveReview('approved')">审核通过</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowDown } from '@element-plus/icons-vue'
import { analyzeRmrbComment, getRmrbCommentArtifact, listRmrbComments, reviewRmrbComment, scanRmrbComments, type RmrbCommentItem } from '@/api/rmrbComments'

const issueDate = ref(new Date().toLocaleDateString('sv-SE'))
const keyword = ref('')
const status = ref('')
const items = ref<RmrbCommentItem[]>([])
const loading = ref(false)
const scanning = ref(false)
const generating = ref('')
const saving = ref(false)
const artifactVisible = ref(false)
const artifactText = ref('')
const artifactTitle = ref('')
const artifactKind = ref('')
const reviewVisible = ref(false)
const current = ref<RmrbCommentItem | null>(null)
const draftMarkdown = ref('')
const reviewNote = ref('')

async function load() {
  loading.value = true
  try { items.value = (await listRmrbComments({ issue_date: issueDate.value, q: keyword.value, status: status.value })).items }
  catch (error) { ElMessage.error(String(error)) }
  finally { loading.value = false }
}
async function scan() {
  scanning.value = true
  try {
    const result = await scanRmrbComments(issueDate.value)
    ElMessage.success(`发现 ${result.discovered} 篇评论文章，原文整理 ${result.originalReady} 篇，失败 ${result.failed} 篇`)
    await load()
  } catch (error) { ElMessage.error(String(error)) }
  finally { scanning.value = false }
}
async function analyze(row: RmrbCommentItem) {
  generating.value = row.id
  try { await analyzeRmrbComment(row.id); ElMessage.success('已提交后台生成，稍后刷新查看'); setTimeout(load, 1500) }
  catch (error) { ElMessage.error(String(error)) }
  finally { generating.value = '' }
}
async function view(row: RmrbCommentItem, kind: string) {
  try { artifactText.value = await getRmrbCommentArtifact(row.id, kind); artifactKind.value = kind; artifactTitle.value = kind.startsWith('original') ? `${row.title}｜原文` : `${row.title}｜三刀解剖`; artifactVisible.value = true }
  catch (error) { ElMessage.error(String(error)) }
}
async function edit(row: RmrbCommentItem) {
  current.value = row
  try { draftMarkdown.value = await getRmrbCommentArtifact(row.id, 'analysis_md'); reviewNote.value = ''; reviewVisible.value = true }
  catch (error) { ElMessage.error(String(error)) }
}
async function saveReview(decision: string) {
  if (!current.value) return
  saving.value = true
  try {
    await reviewRmrbComment(current.value.id, { decision, note: reviewNote.value, markdown: draftMarkdown.value })
    ElMessage.success(decision === 'approved' ? '审核通过' : '审核结果已保存')
    reviewVisible.value = false
    await load()
  } catch (error) { ElMessage.error(String(error)) }
  finally { saving.value = false }
}
function analysisLabel(value: string) { return ({ pending: '待生成', processing: '生成中', draft: '待审核', edited: '已编辑', failed: '失败' } as Record<string, string>)[value] || value }
function reviewLabel(value: string) { return ({ pending: '待审核', approved: '已通过', rejected: '不采用', changes_requested: '需修改' } as Record<string, string>)[value] || value }
onMounted(load)
</script>

<style scoped>
.page{padding:20px;display:flex;flex-direction:column;gap:16px}.toolbar{display:flex;align-items:center;justify-content:space-between;gap:16px}.toolbar h2{margin:0 0 6px}.toolbar p,.muted,.review-meta{color:#777;font-size:13px;margin:0}.actions,.filters{display:flex;gap:10px;align-items:center}.filters{max-width:720px}.document{white-space:pre-wrap;overflow:auto;max-height:70vh;line-height:1.8;font:14px/1.8 ui-monospace,monospace;background:#fafafa;padding:18px;border-radius:6px}.html-preview{width:100%;height:78vh;border:1px solid #eee;border-radius:6px;background:#fff}.review-meta{margin-bottom:12px}.review-note{max-width:240px}@media(max-width:900px){.toolbar{align-items:flex-start;flex-direction:column}.actions{flex-wrap:wrap}.page{padding:12px}}
</style>
