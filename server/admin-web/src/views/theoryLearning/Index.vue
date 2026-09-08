<template>
  <div class="entry-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div><strong>时政学习入口</strong><div class="sub">编排单篇文章的五题分辑、今日入口和长期重点。可用 T0c JSON 一键导入纲要专项卷。</div></div>
          <div>
          <el-button @click="openImport">导入 T0c JSON</el-button>
          <el-button type="primary" @click="openCreate">新建入口</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="entries" stripe>
        <el-table-column label="入口" min-width="260">
          <template #default="{ row }"><strong>{{ row.title }}</strong><div class="sub">原文：{{ row.articleTitle }}</div></template>
        </el-table-column>
        <el-table-column label="位置" width="150">
          <template #default="{ row }">
            <el-tag v-if="row.isDaily" size="small">今日</el-tag>
            <el-tag v-if="row.isEvergreen" size="small" type="success">长期重点</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="questionCount" label="题目" width="80" />
        <el-table-column label="合集" width="90"><template #default="{ row }">{{ row.collectionEnabled ? '已开放' : '未开放' }}</template></el-table-column>
        <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="row.status === 'published' ? 'success' : 'info'">{{ row.status === 'published' ? '已发布' : '草稿' }}</el-tag></template></el-table-column>
        <el-table-column label="校验" min-width="180"><template #default="{ row }"><span :class="row.validationError ? 'error' : 'sub'">{{ row.validationError || '通过' }}</span></template></el-table-column>
        <el-table-column label="操作" width="90"><template #default="{ row }"><el-button link type="primary" @click="openEdit(row)">编辑</el-button></template></el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑学习入口' : '新建学习入口'" width="720px">
      <el-form label-width="110px">
        <el-form-item label="对应文章" required>
          <el-select v-model="form.articleId" filterable :disabled="editing" class="full" @change="loadQuestions">
            <el-option v-for="article in articles" :key="article.id" :label="article.title" :value="article.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="入口标题"><el-input v-model="form.title" maxlength="128" show-word-limit placeholder="留空则使用文章标题" /></el-form-item>
        <el-form-item label="入口说明"><el-input v-model="form.description" type="textarea" :rows="2" maxlength="512" show-word-limit /></el-form-item>
        <el-form-item label="展示位置" required>
          <el-checkbox v-model="form.isDaily">今日内容</el-checkbox>
          <el-checkbox v-model="form.isEvergreen">长期重点</el-checkbox>
        </el-form-item>
        <el-form-item label="展示日期">
          <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期（可空）" end-placeholder="结束日期（可空）" />
        </el-form-item>
        <el-form-item label="题目顺序" required>
          <div class="full">
            <el-button size="small" :disabled="!form.articleId" @click="fillApprovedQuestions">按审核顺序填充</el-button>
            <span class="sub question-note">每行一个题目 ID，保存时按顺序每 5 题分一辑。</span>
            <el-input v-model="questionIdsText" type="textarea" :rows="8" placeholder="q001&#10;q002&#10;q003" />
            <div class="part-preview">
              <el-tag v-for="part in previewParts" :key="part.number" size="small" type="info">第 {{ part.number }} 辑 · {{ part.questionIds.length }} 题</el-tag>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="全文合集"><el-switch v-model="form.collectionEnabled" /><span class="sub switch-note">开启时必须编入该文章全部有效题目</span></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sortOrder" :min="-100000" :max="100000" /></el-form-item>
        <el-form-item label="状态"><el-radio-group v-model="form.status"><el-radio value="draft">草稿</el-radio><el-radio value="published">发布</el-radio></el-radio-group></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="importVisible" title="导入纲要专项 T0c JSON" width="640px">
      <el-input v-model="importJson" type="textarea" :rows="16" placeholder="粘贴 20 题 JSON 全文" />
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="doImport">导入并发布</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchArticles, fetchQuestions } from '@/api/articles'
import type { Article, Question } from '@/types'
import {
  fetchTheoryLearningEntries,
  importT0cPack,
  saveTheoryLearningEntry,
  type LearningPart,
  type TheoryLearningEntry,
} from '@/api/theoryLearning'

const entries = ref<TheoryLearningEntry[]>([])
const articles = ref<Article[]>([])
const availableQuestions = ref<Question[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const importVisible = ref(false)
const importJson = ref('')
const importing = ref(false)
const editing = ref(false)
const dateRange = ref<string[]>([])
const questionIdsText = ref('')
const form = reactive({
  articleId: '', title: '', description: '', isDaily: true, isEvergreen: false,
  collectionEnabled: false, status: 'draft' as 'draft' | 'published', sortOrder: 0,
})
const questionIds = computed(() => questionIdsText.value.split(/[\n,，、\s]+/).map(item => item.trim()).filter(Boolean))
const previewParts = computed<LearningPart[]>(() => Array.from(
  { length: Math.ceil(questionIds.value.length / 5) },
  (_, index) => ({ number: index + 1, title: `第 ${index + 1} 辑`, questionIds: questionIds.value.slice(index * 5, index * 5 + 5) }),
))

async function load() {
  loading.value = true
  try {
    const [entryRows, articleRows] = await Promise.all([
      fetchTheoryLearningEntries(),
      fetchArticles({ page: 1, page_size: 100, status: 'published' }),
    ])
    entries.value = entryRows
    articles.value = articleRows.items
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '加载失败') }
  finally { loading.value = false }
}

function reset() {
  Object.assign(form, { articleId: '', title: '', description: '', isDaily: true, isEvergreen: false, collectionEnabled: false, status: 'draft', sortOrder: 0 })
  dateRange.value = []
  questionIdsText.value = ''
  availableQuestions.value = []
}
function openCreate() { reset(); editing.value = false; dialogVisible.value = true }
function openImport() {
  importJson.value = ''
  importVisible.value = true
}
async function doImport() {
  let payload: Record<string, unknown>
  try {
    payload = JSON.parse(importJson.value)
  } catch {
    ElMessage.error('JSON 无法解析')
    return
  }
  importing.value = true
  try {
    const res = await importT0cPack(payload, false)
    ElMessage.success(`已导入 ${res.title}（${res.questionCount} 题）`)
    importVisible.value = false
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '导入失败')
  } finally {
    importing.value = false
  }
}
async function openEdit(row: TheoryLearningEntry) {
  reset(); editing.value = true
  Object.assign(form, row)
  dateRange.value = row.publishStart || row.publishEnd ? [row.publishStart, row.publishEnd] : []
  questionIdsText.value = row.parts.flatMap(part => part.questionIds).join('\n')
  dialogVisible.value = true
  await loadQuestions(row.articleId)
}
async function loadQuestions(articleId: string) {
  if (!articleId) return
  try { availableQuestions.value = (await fetchQuestions(articleId, 1, 100)).items }
  catch { availableQuestions.value = [] }
}
function fillApprovedQuestions() {
  questionIdsText.value = availableQuestions.value.filter(question => question.status === 'approved' && question.isActive !== false).map(question => question.id).join('\n')
}
async function save() {
  if (!form.articleId) return ElMessage.warning('请选择文章')
  saving.value = true
  try {
    await saveTheoryLearningEntry(form.articleId, {
      title: form.title, description: form.description, isDaily: form.isDaily,
      isEvergreen: form.isEvergreen, parts: previewParts.value,
      collectionEnabled: form.collectionEnabled, status: form.status,
      publishStart: dateRange.value?.[0] || '', publishEnd: dateRange.value?.[1] || '', sortOrder: form.sortOrder,
    })
    ElMessage.success('学习入口已保存')
    dialogVisible.value = false
    await load()
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '保存失败') }
  finally { saving.value = false }
}
onMounted(load)
</script>

<style scoped>
.entry-page { padding: 0; }
.header-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.sub { margin-top: 4px; color: var(--el-text-color-secondary); font-size: 12px; line-height: 1.5; }
.error { color: var(--el-color-danger); font-size: 12px; }
.full { width: 100%; }
.question-note, .switch-note { margin-left: 10px; }
.part-preview { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
</style>
