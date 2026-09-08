<template>
  <div class="edit-page" v-loading="loading">
    <div class="edit-header">
      <div class="edit-header-left">
        <el-button text @click="router.back()">← 返回</el-button>
        <div>
          <h2>{{ isNew ? '新建文章' : '编辑文章' }}</h2>
          <p v-if="!isNew" class="edit-subtitle">{{ form.title || '未命名文章' }}</p>
        </div>
      </div>
      <div class="header-actions">
        <template v-if="!isNew && form.status === 'pending'">
          <el-button type="success" :loading="reviewing" @click="onApprove(false)">审核通过</el-button>
          <el-button type="success" plain :loading="reviewing" @click="onApprove(true)">发布并审核题目</el-button>
          <el-button type="danger" plain :loading="reviewing" @click="onReject">驳回</el-button>
        </template>
        <el-button type="primary" :loading="saving" @click="saveArticle">保存</el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="edit-tabs">
      <el-tab-pane label="文章信息" name="article">
        <el-card shadow="never" class="section-card">
          <el-form label-width="96px" class="article-form">
            <el-row :gutter="20">
              <el-col :span="24">
                <el-form-item label="标题">
                  <el-input v-model="form.title" placeholder="文章标题" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="来源">
                  <el-input v-model="form.source" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="发布日期">
                  <el-input v-model="form.publish_date" placeholder="YYYY-MM-DD" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="分类">
                  <el-tree-select
                    v-model="form.category_id"
                    :data="categoryTree"
                    check-strictly
                    clearable
                    placeholder="选择分类"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="重要度">
                  <el-select v-model="form.importance" style="width: 100%">
                    <el-option v-for="o in IMPORTANCE_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="状态">
                  <el-select v-model="form.status" style="width: 100%" :disabled="isNew">
                    <el-option v-for="s in ARTICLE_STATUSES" :key="s.value" :label="s.label" :value="s.value" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item v-if="!isNew" label="开关">
                  <el-checkbox v-model="form.allow_quiz">允许答题</el-checkbox>
                  <el-checkbox v-model="form.is_daily">今日推荐</el-checkbox>
                  <el-checkbox v-model="form.is_featured">置顶</el-checkbox>
                </el-form-item>
                <el-form-item v-else label=" ">
                  <span class="form-hint">新建默认为待审核，保存后回列表审核</span>
                </el-form-item>
              </el-col>
              <el-col :span="24">
                <el-form-item label="标签">
                  <el-input v-model="tagsText" placeholder="逗号分隔，如：十五五规划,重点必读" />
                </el-form-item>
              </el-col>
              <el-col :span="24">
                <el-form-item label="摘要">
                  <el-input v-model="form.summary" type="textarea" :rows="2" placeholder="简要摘要" />
                </el-form-item>
              </el-col>
              <el-col :span="24">
                <el-form-item label="正文">
                  <div class="content-field">
                    <div class="content-toolbar">
                      <el-button size="small" plain :loading="inferring" @click="applyInferredMetadata(true)">
                        从正文识别
                      </el-button>
                      <span class="form-hint">粘贴人民日报正文后可自动或手动识别标题、来源、标签、分类等</span>
                    </div>
                    <el-input
                      v-model="form.content"
                      type="textarea"
                      :rows="16"
                      placeholder="粘贴文章正文（首行可为标题）"
                      @paste="onContentPaste"
                    />
                  </div>
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane :label="`题目管理 (${qTotal})`" name="questions" :disabled="isNew">
        <el-card shadow="never" class="section-card">
          <div class="questions-toolbar">
            <div class="toolbar-left">
              <el-button type="primary" :disabled="isNew" @click="openQuestionDialog()">新增题目</el-button>
              <el-button plain :disabled="isNew" @click="openImportDialog">批量导入</el-button>
              <el-button
                v-if="pendingQuestionCount"
                type="success"
                plain
                @click="approveAllQuestions"
              >
                通过全部待审（{{ pendingQuestionCount }}）
              </el-button>
            </div>
          </div>

          <div v-if="selectedQuestionIds.length" class="q-batch-bar">
            <span>已选 {{ selectedQuestionIds.length }} 题</span>
            <el-button size="small" type="success" @click="batchApproveSelected">批量通过</el-button>
            <el-button size="small" type="danger" plain @click="batchDeleteSelected">批量删除</el-button>
          </div>

          <el-empty v-if="!isNew && !questions.length" description="暂无题目，请新增或批量导入 Markdown 题库" />
          <template v-else-if="!isNew">
            <el-table :data="questions" stripe @selection-change="onQuestionSelectionChange">
              <el-table-column type="selection" width="48" />
              <el-table-column label="题干" min-width="280" show-overflow-tooltip>
                <template #default="{ row }">{{ row.stem }}</template>
              </el-table-column>
              <el-table-column label="题型" width="80">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.type === 'multiple' ? 'warning' : 'info'">
                    {{ questionTypeLabel(row.type) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="状态" width="88">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.status === 'approved' ? 'success' : row.status === 'pending' ? 'warning' : 'info'">
                    {{ questionStatusLabel(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" @click="openQuestionDialog(row)">编辑</el-button>
                  <el-button link type="danger" @click="removeQuestion(row.id)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-pagination
              v-model:current-page="qPage"
              v-model:page-size="qPageSize"
              :total="qTotal"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next"
              class="pager"
              @current-change="loadQuestions"
              @size-change="onQuestionPageSizeChange"
            />
          </template>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="qDialogVisible" :title="editingQuestion ? '编辑题目' : '新增题目'" width="640px">
      <el-form label-width="80px">
        <el-form-item label="题型">
          <el-select v-model="qForm.type" style="width: 160px">
            <el-option v-for="t in QUESTION_TYPES" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="题干">
          <el-input v-model="qForm.stem" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="选项">
          <el-input v-model="qForm.optionsText" type="textarea" :rows="3" placeholder="每行一个选项" />
        </el-form-item>
        <el-form-item label="正确答案">
          <el-input v-model="qForm.correctAnswerText" placeholder="单选/判断填一项；多选用逗号分隔" />
        </el-form-item>
        <el-form-item label="解析">
          <el-input v-model="qForm.analysis" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="原文">
          <el-input v-model="qForm.source_sentence" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="qDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="qSaving" @click="saveQuestion">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importDialogVisible" title="批量导入题目" width="720px">
      <p class="import-hint">
        粘贴 Markdown 格式题库（支持单选/多选），格式示例：<br>
        <code>**1. 题干**</code> → <code>A. 选项</code> … → <code>&gt; **答案：B**</code> → <code>&gt; **原文依据：** …</code>
      </p>
      <el-input v-model="importMarkdown" type="textarea" :rows="16" placeholder="粘贴完整 MD 文档内容…" />
      <el-checkbox v-model="importAsPending" style="margin-top: 12px">导入为待审核（取消则直接生效）</el-checkbox>
      <el-checkbox v-model="importReplaceExisting" style="margin-top: 8px; display: block">
        覆盖已有题目（删除本文全部旧题后再导入，推荐用于修正原文/解析）
      </el-checkbox>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="submitImport">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  approveArticle,
  approveArticleQuestions,
  batchApproveQuestions,
  batchDeleteQuestions,
  createArticle,
  createQuestion,
  deleteQuestion,
  fetchArticle,
  fetchQuestions,
  importQuestions,
  inferArticleMetadata,
  rejectArticle,
  updateArticle,
  updateQuestion,
} from '@/api/articles'
import { fetchCategories } from '@/api/categories'
import {
  ARTICLE_STATUSES,
  IMPORTANCE_OPTIONS,
  QUESTION_STATUSES,
  QUESTION_TYPES,
  type Category,
  type Question,
} from '@/types'

const route = useRoute()
const router = useRouter()
const isNew = computed(() => route.name === 'article-new')
const articleId = computed(() => (route.params.id as string) || '')

const loading = ref(false)
const saving = ref(false)
const inferring = ref(false)
const reviewing = ref(false)
const activeTab = ref('article')
const questions = ref<Question[]>([])
const selectedQuestions = ref<Question[]>([])
const categories = ref<Category[]>([])
const tagsText = ref('')
const qPage = ref(1)
const qPageSize = ref(20)
const qTotal = ref(0)
const pendingQuestionCount = ref(0)

const form = reactive({
  title: '',
  source: '',
  publish_date: '',
  summary: '',
  content: '',
  category_id: null as string | null,
  importance: 3,
  status: 'pending',
  allow_quiz: true,
  is_daily: false,
  is_featured: false,
})

const categoryTree = computed(() => mapCategoryTree(categories.value))
const selectedQuestionIds = computed(() => selectedQuestions.value.map((q) => q.id))

function onQuestionSelectionChange(rows: Question[]) {
  selectedQuestions.value = rows
}

function questionStatusLabel(value?: string) {
  return QUESTION_STATUSES.find((s) => s.value === value)?.label || value || '-'
}

function questionTypeLabel(value?: string) {
  return QUESTION_TYPES.find((t) => t.value === value)?.label || value || '-'
}

function mapCategoryTree(list: Category[]): Array<{ value: string; label: string; children?: unknown[] }> {
  return list.map((c) => ({
    value: c.id,
    label: c.name,
    children: c.children?.length ? mapCategoryTree(c.children) : undefined,
  }))
}

function resetNewForm() {
  form.title = ''
  form.source = '手动录入'
  form.publish_date = new Date().toISOString().slice(0, 10)
  form.summary = ''
  form.content = ''
  form.category_id = null
  form.importance = 3
  form.status = 'pending'
  form.allow_quiz = true
  form.is_daily = false
  form.is_featured = false
  tagsText.value = ''
  questions.value = []
  qTotal.value = 0
  pendingQuestionCount.value = 0
  activeTab.value = 'article'
}

async function applyInferredMetadata(overwrite = false) {
  if (!form.content.trim()) {
    ElMessage.warning('请先粘贴正文')
    return
  }
  inferring.value = true
  try {
    const meta = await inferArticleMetadata({
      content: form.content,
      title: form.title,
    })
    if (overwrite || !form.title.trim()) form.title = meta.title
    if (overwrite || !form.summary.trim()) form.summary = meta.summary
    if (overwrite || !form.source.trim() || form.source === '手动录入') form.source = meta.source
    if (overwrite || !form.publish_date) form.publish_date = meta.publishDate
    if (overwrite || !form.category_id) form.category_id = meta.categoryId || null
    if (overwrite || form.importance === 3) form.importance = meta.importance
    if (overwrite || !tagsText.value.trim()) tagsText.value = (meta.tags || []).join(',')
    if (meta.content && (overwrite || form.content !== meta.content)) {
      form.content = meta.content
    }
    const filled = [
      meta.title && '标题',
      meta.summary && '摘要',
      meta.source && meta.source !== '手动录入' && '来源',
      meta.tags?.length && '标签',
      meta.categoryName && '分类',
    ].filter(Boolean)
    ElMessage.success(filled.length ? `已识别：${filled.join('、')}` : '已处理正文')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '识别失败')
  } finally {
    inferring.value = false
  }
}

async function onContentPaste() {
  await nextTick()
  if (!form.content.trim()) return
  await applyInferredMetadata(false)
}

async function loadQuestions() {
  const qRes = await fetchQuestions(articleId.value, qPage.value, qPageSize.value)
  questions.value = qRes.items
  qTotal.value = qRes.total
  pendingQuestionCount.value = qRes.pending_total ?? 0
  selectedQuestions.value = []
}

function onQuestionPageSizeChange() {
  qPage.value = 1
  loadQuestions()
}

async function load() {
  if (isNew.value) {
    resetNewForm()
    loading.value = true
    try {
      categories.value = await fetchCategories()
    } catch (e) {
      ElMessage.error(e instanceof Error ? e.message : '加载分类失败')
    } finally {
      loading.value = false
    }
    return
  }
  loading.value = true
  try {
    const id = articleId.value
    const [article, cats] = await Promise.all([fetchArticle(id), fetchCategories()])
    form.title = article.title
    form.source = article.source
    form.publish_date = article.publishDate
    form.summary = article.summary
    form.content = article.content
    form.category_id = article.categoryId || null
    form.importance = article.importance || 3
    form.status = article.status || 'draft'
    form.allow_quiz = article.allowQuiz !== false
    form.is_daily = !!article.isDaily
    form.is_featured = !!article.isFeatured
    tagsText.value = (article.tags || []).join(',')
    categories.value = cats
    await loadQuestions()
  } finally {
    loading.value = false
  }
}

async function saveArticle() {
  if (!form.title.trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  if (!form.content.trim()) {
    ElMessage.warning('请填写正文')
    return
  }
  saving.value = true
  try {
    const payload = {
      title: form.title.trim(),
      source: form.source.trim() || '手动录入',
      publish_date: form.publish_date || new Date().toISOString().slice(0, 10),
      summary: form.summary.trim() || form.title.trim().slice(0, 120),
      content: form.content.trim(),
      category_id: form.category_id,
      importance: form.importance,
      status: isNew.value ? 'pending' : form.status,
      allow_quiz: form.allow_quiz,
      is_daily: form.is_daily,
      is_featured: form.is_featured,
      is_published: false,
      tags: tagsText.value.split(/[,，]/).map((s) => s.trim()).filter(Boolean),
      auto_generate_questions: false,
    }
    if (isNew.value) {
      await createArticle(payload)
      ElMessage.success('已保存为待审核，请在列表中审核')
      router.push({ name: 'articles', query: { status: 'pending' } })
      return
    }
    await updateArticle(articleId.value, {
      ...payload,
      is_published: form.status === 'published',
    })
    ElMessage.success('文章已保存')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function onApprove(approveQuestions = false) {
  reviewing.value = true
  try {
    await approveArticle(articleId.value)
    form.status = 'published'
    if (approveQuestions && pendingQuestionCount.value) {
      const res = await approveArticleQuestions(articleId.value)
      await loadQuestions()
      ElMessage.success(`文章已发布，并审核通过 ${res.count} 道题目`)
    } else {
      ElMessage.success('文章已发布')
    }
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '操作失败')
  } finally {
    reviewing.value = false
  }
}

async function onReject() {
  await ElMessageBox.confirm('驳回后学员端将不可见，确定吗？', '驳回文章', { type: 'warning' })
  reviewing.value = true
  try {
    await rejectArticle(articleId.value)
    form.status = 'rejected'
    form.is_daily = false
    ElMessage.success('文章已驳回')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '操作失败')
  } finally {
    reviewing.value = false
  }
}

async function approveAllQuestions() {
  const res = await approveArticleQuestions(articleId.value)
  ElMessage.success(`已通过 ${res.count} 道题目`)
  await loadQuestions()
}

async function batchApproveSelected() {
  const pendingIds = selectedQuestions.value.filter((q) => q.status === 'pending').map((q) => q.id)
  const ids = pendingIds.length ? pendingIds : selectedQuestionIds.value
  if (!ids.length) return
  try {
    const res = await batchApproveQuestions(ids)
    ElMessage.success(`已通过 ${res.count} 道题目`)
    await loadQuestions()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '操作失败')
  }
}

async function batchDeleteSelected() {
  await ElMessageBox.confirm(`确定删除选中的 ${selectedQuestionIds.value.length} 道题目？`, '批量删除', { type: 'warning' })
  try {
    const res = await batchDeleteQuestions(selectedQuestionIds.value)
    ElMessage.success(`已删除 ${res.count} 道题目`)
    if (questions.value.length === selectedQuestionIds.value.length && qPage.value > 1) {
      qPage.value -= 1
    }
    await loadQuestions()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '删除失败')
  }
}

const importDialogVisible = ref(false)
const importMarkdown = ref('')
const importAsPending = ref(true)
const importReplaceExisting = ref(true)
const importing = ref(false)

function openImportDialog() {
  importMarkdown.value = ''
  importAsPending.value = true
  importReplaceExisting.value = true
  importDialogVisible.value = true
}

async function submitImport() {
  if (!importMarkdown.value.trim()) {
    ElMessage.warning('请粘贴 Markdown 内容')
    return
  }
  importing.value = true
  try {
    const res = await importQuestions(articleId.value, {
      markdown: importMarkdown.value,
      pending: importAsPending.value,
      replace_existing: importReplaceExisting.value,
    })
    importDialogVisible.value = false
    activeTab.value = 'questions'
    qPage.value = 1
    await loadQuestions()
    const warn = res.parse_warnings?.length ? `（${res.parse_warnings.length} 条解析提示）` : ''
    ElMessage.success(`已导入 ${res.count} 道题目${warn}`)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '导入失败')
  } finally {
    importing.value = false
  }
}

const qDialogVisible = ref(false)
const qSaving = ref(false)
const editingQuestion = ref<Question | null>(null)
const qForm = reactive({
  type: 'single',
  stem: '',
  optionsText: '',
  correctAnswerText: '',
  analysis: '',
  source_sentence: '',
})

function openQuestionDialog(q?: Question) {
  editingQuestion.value = q || null
  qForm.type = q?.type || 'single'
  qForm.stem = q?.stem || ''
  qForm.optionsText = (q?.options || []).join('\n')
  qForm.correctAnswerText = Array.isArray(q?.correctAnswer)
    ? q!.correctAnswer.join(',')
    : q?.correctAnswer || ''
  qForm.analysis = q?.analysis || ''
  qForm.source_sentence = q?.sourceSentence || ''
  qDialogVisible.value = true
}

async function saveQuestion() {
  qSaving.value = true
  try {
    const options = qForm.optionsText.split('\n').map((s) => s.trim()).filter(Boolean)
    const correctAnswer = qForm.type === 'multiple'
      ? qForm.correctAnswerText.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
      : qForm.correctAnswerText.trim()
    const payload = {
      article_id: articleId.value,
      type: qForm.type,
      stem: qForm.stem,
      options,
      correct_answer: correctAnswer,
      analysis: qForm.analysis,
      source_sentence: qForm.source_sentence,
      status: 'approved',
      is_active: true,
    }
    if (editingQuestion.value) {
      await updateQuestion(editingQuestion.value.id, payload)
    } else {
      await createQuestion(payload)
    }
    qDialogVisible.value = false
    await loadQuestions()
    ElMessage.success('题目已保存')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    qSaving.value = false
  }
}

async function removeQuestion(id: string) {
  await ElMessageBox.confirm('确定删除该题目？', '提示', { type: 'warning' })
  try {
    await deleteQuestion(id)
    ElMessage.success('已删除')
    if (questions.value.length === 1 && qPage.value > 1) {
      qPage.value -= 1
    }
    await loadQuestions()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '删除失败')
  }
}

watch(() => route.fullPath, load, { immediate: true })
</script>

<style scoped>
.edit-page {
  max-width: 1180px;
  margin: 0 auto;
}
.edit-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  padding: 16px 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.edit-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.edit-header h2 {
  margin: 0;
  font-size: 18px;
  line-height: 1.3;
}
.edit-subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 520px;
}
.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}
.edit-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
  background: #fff;
  padding: 0 16px;
  border-radius: 8px 8px 0 0;
}
.edit-tabs :deep(.el-tabs__content) {
  padding: 0;
}
.section-card {
  border-radius: 0 0 8px 8px;
  border-top: none;
}
.article-form {
  padding-top: 8px;
}
.questions-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}
.toolbar-left {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.q-batch-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding: 10px 12px;
  background: #f0f9eb;
  border-radius: 6px;
  font-size: 13px;
}
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}
.import-hint {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  margin: 0 0 12px;
}
.import-hint code {
  background: #f5f7fa;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 12px;
}
.form-hint {
  font-size: 12px;
  color: #909399;
}
.content-field {
  width: 100%;
}
.content-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
</style>
