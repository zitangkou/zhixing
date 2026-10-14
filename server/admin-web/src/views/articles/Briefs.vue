<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http, { getData } from '@/api/http'

interface Point {
  id: string
  title: string
  articleId: string
  articleTitle: string
  highlights: string
  isPublished: boolean
  isKey: boolean
  sortOrder: number
  questionCount: number
  parentId: string
  parentTitle: string
}
interface ArticleOpt {
  id: string
  title: string
}

const items = ref<Point[]>([])
const articles = ref<ArticleOpt[]>([])
const loading = ref(false)
const open = ref(false)
const form = ref({
  id: '',
  title: '',
  articleId: '',
  highlights: '',
  isPublished: false,
  isKey: false,
  sortOrder: 0,
  parentId: '',
})

const parents = computed(() => items.value.filter((row) => !row.parentId && row.id !== form.value.id))

async function load() {
  loading.value = true
  try {
    const data = await getData<{ items: Point[] }>(http.get('/admin/theory-briefs'))
    items.value = data.items
  } finally {
    loading.value = false
  }
}

async function loadArticles() {
  const data = await getData<{ items: ArticleOpt[] }>(http.get('/admin/articles', { params: { page: 1, page_size: 100 } }))
  articles.value = data.items
}

function blank() {
  form.value = { id: '', title: '', articleId: '', highlights: '', isPublished: false, isKey: false, sortOrder: 0, parentId: '' }
  open.value = true
}

function edit(row: Point) {
  form.value = {
    id: row.id,
    title: row.title,
    articleId: row.articleId,
    highlights: row.highlights,
    isPublished: row.isPublished,
    isKey: row.isKey,
    sortOrder: row.sortOrder,
    parentId: row.parentId || '',
  }
  open.value = true
}

function payload() {
  return {
    title: form.value.title,
    articleId: form.value.articleId || null,
    highlights: form.value.highlights,
    isPublished: form.value.isPublished,
    isKey: form.value.isKey,
    sortOrder: form.value.sortOrder,
    parentId: form.value.parentId || null,
  }
}

async function save() {
  const body = payload()
  if (form.value.id) await getData(http.put(`/admin/theory-briefs/${form.value.id}`, body))
  else await getData(http.post('/admin/theory-briefs', body))
  ElMessage.success('已保存')
  open.value = false
  await load()
}

async function remove(id: string) {
  await getData(http.delete(`/admin/theory-briefs/${id}`))
  await load()
}

onMounted(() => {
  load()
  loadArticles()
})
</script>

<template>
  <div>
    <div style="margin-bottom: 12px">
      <el-button type="primary" @click="blank">新增时政要点</el-button>
    </div>
    <el-table v-loading="loading" :data="items">
      <el-table-column prop="title" label="标题" min-width="180" />
      <el-table-column prop="parentTitle" label="所属要点" min-width="140" />
      <el-table-column prop="articleTitle" label="原文" min-width="180" />
      <el-table-column prop="questionCount" label="套题" width="80" />
      <el-table-column label="重点" width="70">
        <template #default="{ row }">{{ row.isKey ? '是' : '' }}</template>
      </el-table-column>
      <el-table-column label="发布" width="80">
        <template #default="{ row }">{{ row.isPublished ? '是' : '否' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link type="primary" @click="edit(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-drawer v-model="open" title="时政要点" size="480px">
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
        <el-form-item label="时政要点原文">
          <el-select v-model="form.articleId" filterable clearable placeholder="选择文章" style="width: 100%">
            <el-option v-for="a in articles" :key="a.id" :label="a.title" :value="a.id" />
          </el-select>
          <div class="hint">模拟套题用这篇原文里已经通过的题目，不在这里重新出题。</div>
        </el-form-item>
        <el-form-item label="摘要">
          <el-input v-model="form.highlights" type="textarea" :rows="3" placeholder="原文里的一段摘要，显示在学员端列表" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sortOrder" />
        </el-form-item>
        <el-form-item label="重点">
          <el-switch v-model="form.isKey" />
        </el-form-item>
        <el-form-item label="对学员发布">
          <el-switch v-model="form.isPublished" />
        </el-form-item>
        <el-button type="primary" @click="save">保存</el-button>
      </el-form>
    </el-drawer>
  </div>
</template>

<style scoped>
.hint { margin-top: 6px; color: var(--el-text-color-secondary); font-size: 12px; line-height: 1.5; }
</style>
