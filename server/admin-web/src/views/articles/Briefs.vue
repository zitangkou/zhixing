<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http, { getData } from '@/api/http'

interface Point {
  id: string
  title: string
  highlights: string
  isPublished: boolean
  isKey: boolean
  sortOrder: number
  questionCount: number
  parentId: string
  parentTitle: string
}

const items = ref<Point[]>([])
const parentItems = ref<Pick<Point, 'id' | 'title'>[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const open = ref(false)
const saving = ref(false)
const importMarkdown = ref('')
const previewText = ref('')
const questionsOpen = ref(false)
const questionEditOpen = ref(false)
const questions = ref<{ id: string; stem: string; options?: string[]; correctAnswer?: string | string[]; analysis?: string }[]>([])
const questionForm = ref({ id: '', stem: '', optionsText: '', answer: '', analysis: '' })
const form = ref({
  id: '',
  title: '',
  highlights: '',
  isPublished: false,
  isKey: false,
  sortOrder: 0,
  parentId: '',
})

const parents = computed(() => parentItems.value.filter((row) => row.id !== form.value.id))

async function load() {
  loading.value = true
  try {
    const data = await getData<{
      items: Point[]
      parents: Pick<Point, 'id' | 'title'>[]
      total: number
    }>(http.get('/admin/theory-briefs', { params: { page: page.value, page_size: pageSize.value } }))
    items.value = data.items
    parentItems.value = data.parents
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function blank() {
  form.value = { id: '', title: '', highlights: '', isPublished: false, isKey: false, sortOrder: 0, parentId: '' }
  importMarkdown.value = ''
  previewText.value = ''
  open.value = true
}

function edit(row: Point) {
  form.value = {
    id: row.id,
    title: row.title,
    highlights: row.highlights,
    isPublished: row.isPublished,
    isKey: row.isKey,
    sortOrder: row.sortOrder,
    parentId: row.parentId || '',
  }
  importMarkdown.value = ''
  previewText.value = ''
  open.value = true
}

function payload() {
  const existing = items.value.find((row) => row.id === form.value.id)
  return {
    title: form.value.title,
    highlights: form.value.highlights,
    isPublished: existing?.isPublished ?? false,
    isKey: existing?.isKey ?? false,
    sortOrder: existing?.sortOrder ?? 0,
    parentId: form.value.parentId || null,
  }
}

async function previewMarkdown() {
  const markdown = importMarkdown.value.trim()
  if (markdown.length < 10) {
    previewText.value = '请先粘贴套题'
    return
  }
  const data = await getData<{ count: number; parseWarnings: string[] }>(
    http.post('/admin/theory-briefs/preview-questions', { markdown }),
  )
  if (!data.count && !data.parseWarnings.length) {
    previewText.value = '没有识别到题目'
    return
  }
  const head = `识别到 ${data.count} 道题`
  previewText.value = data.parseWarnings.length
    ? `${head}，${data.parseWarnings.length} 处格式问题：\n${data.parseWarnings.join('\n')}`
    : `${head}，格式没有问题`
}

async function save() {
  const markdown = importMarkdown.value.trim()
  if (markdown && markdown.length < 10) {
    ElMessage.warning('套题内容太短')
    return
  }
  saving.value = true
  try {
    const creating = !form.value.id
    const body = payload()
    const saved = form.value.id
      ? await getData<Point>(http.put(`/admin/theory-briefs/${form.value.id}`, body))
      : await getData<Point>(http.post('/admin/theory-briefs', body))
    form.value.id = saved.id
    if (creating) page.value = 1
    if (!markdown) {
      ElMessage.success('已保存')
      open.value = false
      await load()
      return
    }
    const data = await getData<{ count: number; parseWarnings?: string[] }>(
      http.post(`/admin/theory-briefs/${saved.id}/import-questions`, {
        markdown,
        pending: false,
        replaceExisting: true,
      }),
    )
    const warn = data.parseWarnings?.length ? `，${data.parseWarnings.length} 条解析提示` : ''
    ElMessage.success(`已保存，导入 ${data.count} 道题目${warn}`)
    importMarkdown.value = ''
    open.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function remove(id: string) {
  await getData(http.delete(`/admin/theory-briefs/${id}`))
  if (items.value.length === 1 && page.value > 1) page.value -= 1
  await load()
}

function changePageSize(value: number) {
  pageSize.value = value
  page.value = 1
  void load()
}

async function openQuestions() {
  if (!form.value.id) return
  const data = await getData<{ items: typeof questions.value }>(
    http.get('/admin/questions', { params: { theory_point_id: form.value.id, page: 1, page_size: 200 } }),
  )
  questions.value = data.items
  questionsOpen.value = true
}

function editQuestion(row: (typeof questions.value)[number]) {
  const answer = Array.isArray(row.correctAnswer) ? row.correctAnswer.join('，') : (row.correctAnswer || '')
  questionForm.value = {
    id: row.id,
    stem: row.stem,
    optionsText: (row.options || []).join('\n'),
    answer,
    analysis: row.analysis || '',
  }
  questionEditOpen.value = true
}

async function saveQuestion() {
  const options = questionForm.value.optionsText.split('\n').map((line) => line.trim()).filter(Boolean)
  const answer = questionForm.value.answer.includes('，')
    ? questionForm.value.answer.split('，').map((part) => part.trim()).filter(Boolean)
    : questionForm.value.answer.trim()
  await getData(http.put(`/admin/questions/${questionForm.value.id}`, {
    stem: questionForm.value.stem,
    options,
    correct_answer: answer,
    analysis: questionForm.value.analysis,
  }))
  ElMessage.success('题目已保存')
  questionEditOpen.value = false
  await openQuestions()
}

function onSort(row: Point, value: number | undefined) {
  const next = value ?? 0
  if (next === row.sortOrder) return
  patchRow(row, { sortOrder: next })
}

async function patchRow(row: Point, patch: Partial<Pick<Point, 'isPublished' | 'isKey' | 'sortOrder'>>) {
  const previous = { isPublished: row.isPublished, isKey: row.isKey, sortOrder: row.sortOrder }
  Object.assign(row, patch)
  try {
    await getData(http.put(`/admin/theory-briefs/${row.id}`, {
      title: row.title,
      highlights: row.highlights,
      isPublished: row.isPublished,
      isKey: row.isKey,
      sortOrder: row.sortOrder,
      parentId: row.parentId || null,
    }))
  } catch {
    Object.assign(row, previous)
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div style="margin-bottom: 12px">
      <el-button type="primary" @click="blank">新增时政要点</el-button>
    </div>
    <el-table v-loading="loading" :data="items">
      <el-table-column prop="title" label="标题" min-width="180" />
      <el-table-column prop="parentTitle" label="所属要点" min-width="140" />
      <el-table-column prop="questionCount" label="套题" width="80" />
      <el-table-column label="重点" width="80">
        <template #default="{ row }">
          <el-switch :model-value="row.isKey" @change="(value: boolean) => patchRow(row, { isKey: value })" />
        </template>
      </el-table-column>
      <el-table-column label="启用" width="80">
        <template #default="{ row }">
          <el-switch :model-value="row.isPublished" @change="(value: boolean) => patchRow(row, { isPublished: value })" />
        </template>
      </el-table-column>
      <el-table-column label="排序" width="130">
        <template #default="{ row }">
          <el-input-number :model-value="row.sortOrder" controls-position="right" @change="(value: number | undefined) => onSort(row, value)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link type="primary" @click="edit(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      v-model:current-page="page"
      :page-size="pageSize"
      :page-sizes="[20, 50, 100]"
      :total="total"
      layout="total, sizes, prev, pager, next, jumper"
      @current-change="load"
      @size-change="changePageSize"
    />

    <el-drawer v-model="open" title="时政要点" size="640px">
      <el-form label-position="top">
        <el-form-item label="标题">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="所属要点">
          <el-select v-model="form.parentId" filterable clearable placeholder="留空则是一级要点" style="width: 100%">
            <el-option v-for="p in parents" :key="p.id" :label="p.title" :value="p.id" />
          </el-select>
          <div class="hint">选了所属要点，这条就是它的小节。小节不能再挂小节。</div>
        </el-form-item>
        <el-form-item label="套题">
          <el-input v-model="importMarkdown" type="textarea" :rows="12" placeholder="可选。粘贴 Markdown 后和要点一起保存。一条要点只有一套题，再次粘贴会覆盖。" />
          <div class="hint">
            <code>**1. 题干**</code> → <code>A. 选项</code> → <code>&gt; **答案：B**</code> → <code>&gt; **解析：** …</code>
            <el-button link type="primary" @click="previewMarkdown">验证格式</el-button>
            <el-button v-if="form.id" link type="primary" @click="openQuestions">查看已有题目</el-button>
          </div>
          <pre v-if="previewText" class="preview">{{ previewText }}</pre>
        </el-form-item>
        <el-form-item label="摘要">
          <el-input v-model="form.highlights" type="textarea" :rows="3" placeholder="原文里的一段摘要，显示在学员端列表" />
        </el-form-item>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </el-form>
    </el-drawer>

    <el-dialog v-model="questionsOpen" title="这一套题" width="760px">
      <el-table :data="questions" empty-text="还没有题目">
        <el-table-column prop="stem" label="题干" min-width="240" />
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button link type="primary" @click="editQuestion(row)">修改</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <el-dialog v-model="questionEditOpen" title="修改题目" width="640px">
      <el-form label-position="top">
        <el-form-item label="题干"><el-input v-model="questionForm.stem" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="选项，每行一个"><el-input v-model="questionForm.optionsText" type="textarea" :rows="4" /></el-form-item>
        <el-form-item label="答案"><el-input v-model="questionForm.answer" /></el-form-item>
        <el-form-item label="解析"><el-input v-model="questionForm.analysis" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="questionEditOpen = false">取消</el-button>
        <el-button type="primary" @click="saveQuestion">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.hint { margin-top: 6px; color: var(--el-text-color-secondary); font-size: 12px; line-height: 1.5; }
.preview { margin-top: 8px; white-space: pre-wrap; font-size: 12px; line-height: 1.5; }
</style>
