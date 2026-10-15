<template>
  <div class="page">
    <header>
      <div>
        <h2>金句管理</h2>
        <p>先审核是否符合金句素材，通过后再启用；仿写可在确认运营用途时按需生成。</p>
      </div>
      <div class="actions">
        <el-button v-if="canWrite" :loading="running" @click="run">整理今日</el-button>
        <el-button type="primary" @click="edit()">新增</el-button>
      </div>
    </header>

    <div class="filters">
      <el-radio-group v-model="status" @change="filter">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="pending">待确认</el-radio-button>
        <el-radio-button value="confirmed">已启用</el-radio-button>
      </el-radio-group>
      <el-input v-model="search" clearable placeholder="搜索原句" @keyup.enter="filter" @clear="filter" />
    </div>

    <el-table v-loading="loading" :data="items">
      <el-table-column label="金句" min-width="280">
        <template #default="{ row }">
          <div class="quote">{{ row.text }}</div>
          <div class="meta">{{ row.topics.join('、') || row.component }} · {{ row.articleTitle }}</div>
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
    <el-pagination v-model:current-page="page" :total="total" :page-size="20" layout="total, prev, pager, next" @current-change="load" />

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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import * as api from '@/api/dailyQuotes'

const auth = useAuthStore()
const canWrite = computed(() => auth.hasPermission('rmrb:write'))
const today = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai' }).format(new Date())
const components = ['开头点题', '分论点标题', '论证句', '结尾升华']
const status = ref('')
const search = ref('')
const page = ref(1)
const total = ref(0)
const items = ref<api.DailyQuote[]>([])
const loading = ref(false)
const saving = ref(false)
const running = ref(false)
const editing = ref(false)
const draft = ref<api.DailyQuote | null>(null)
const topicsInput = ref('')
const highlightsInput = ref('')

function split(s: string) {
  return s.split(/[，,]/).map((x) => x.trim()).filter(Boolean)
}

async function load() {
  loading.value = true
  try {
    const data = await api.listQuotes({ q: search.value, status: status.value, page: page.value })
    items.value = data.items
    total.value = data.total
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

async function audit(row: api.DailyQuote) {
  try {
    await ElMessageBox.confirm('这条是否符合金句素材？', '审核', {
      confirmButtonText: '符合',
      cancelButtonText: '不符合',
      distinguishCancelAndClose: true,
    })
    await api.saveQuote({ ...row, auditStatus: 'passed', enabled: row.enabled })
  } catch (e) {
    if (e === 'cancel') {
      await api.saveQuote({ ...row, auditStatus: 'rejected', enabled: false, reviewStatus: 'pending' })
    } else if (e !== 'close') {
      ElMessage.error(e instanceof Error ? e.message : '审核失败')
      return
    } else return
  }
  await load()
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
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '整理失败')
  } finally {
    running.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
header, .actions, .filters { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
header { justify-content: space-between; }
header p { margin: 4px 0 0; color: var(--el-text-color-secondary); }
.filters .el-input { width: 220px; }
.quote { line-height: 1.6; }
.meta { margin-top: 4px; color: var(--el-text-color-secondary); font-size: 12px; }
.example { display: flex; flex-direction: column; gap: 8px; margin: 12px 0; }
.save { margin-top: 16px; }
</style>
