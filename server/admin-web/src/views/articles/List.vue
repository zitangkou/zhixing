<template>
  <div class="page">
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索标题" clearable style="width: 240px" @keyup.enter="load" />
      <el-select v-model="status" placeholder="状态" clearable style="width: 140px" @change="load">
        <el-option v-for="s in ARTICLE_STATUSES" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button @click="filterPending">待审核</el-button>
      <el-button type="success" @click="router.push({ name: 'article-new' })">新建文章</el-button>
      <el-button type="primary" plain @click="openArticleImportDialog">导入 Markdown</el-button>
    </div>

    <div v-if="selectedIds.length" class="batch-bar">
      <span>已选 {{ selectedIds.length }} 篇</span>
      <el-button size="small" type="success" :loading="batchLoading" @click="onBatchApprove(true)">
        批量发布并审核题目
      </el-button>
      <el-button size="small" type="success" plain :loading="batchLoading" @click="onBatchApprove(false)">
        仅批量发布
      </el-button>
      <el-button size="small" type="warning" plain :loading="batchLoading" @click="openCategoryDialog">
        批量设分类
      </el-button>
      <el-button size="small" type="danger" plain :loading="batchLoading" @click="onBatchReject">
        批量驳回
      </el-button>
      <el-button size="small" type="danger" :loading="batchLoading" @click="onBatchDelete">
        批量删除
      </el-button>
    </div>

    <ListState
      :loading="loading"
      :error="loadError"
      :has-data="items.length > 0"
      :empty-text="listEmptyText"
      @retry="load"
    >
      <template #empty-action>
        <el-button type="success" @click="router.push({ name: 'article-new' })">新建文章</el-button>
      </template>
      <el-table
        v-loading="loading && items.length > 0"
        :data="items"
        stripe
        @selection-change="onSelectionChange"
      >
      <el-table-column type="selection" width="48" />
      <el-table-column prop="title" label="标题" min-width="240" show-overflow-tooltip />
      <el-table-column prop="source" label="来源" width="100" />
      <el-table-column label="分类" width="120">
        <template #default="{ row }">{{ row.categoryName || '-' }}</template>
      </el-table-column>
      <el-table-column label="重要度" width="80">
        <template #default="{ row }">{{ row.importanceLabel || row.importance }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="publishDate" label="日期" width="110" />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="router.push(`/articles/${row.id}`)">编辑</el-button>
          <el-button link type="primary" @click="openQuickEdit(row)">快速编辑</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      :page-sizes="[10, 20, 50]"
      layout="total, sizes, prev, pager, next"
      class="pager"
      @current-change="load"
      @size-change="onPageSizeChange"
    />
    </ListState>

    <el-dialog v-model="categoryDialogVisible" title="批量设置分类" width="480px">
      <el-tree-select
        v-model="batchCategoryId"
        :data="categoryTree"
        check-strictly
        clearable
        placeholder="选择分类（留空则清除分类）"
        style="width: 100%"
      />
      <template #footer>
        <el-button @click="categoryDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="batchLoading" @click="submitBatchCategory">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="quickEditVisible" :title="`快速编辑：${quickEditTitle}`" width="560px" destroy-on-close>
      <el-form :model="quickEditForm" label-width="96px">
        <el-form-item label="来源">
          <el-input v-model="quickEditForm.source" placeholder="如：人民日报" />
        </el-form-item>
        <el-form-item label="发布日期">
          <el-date-picker
            v-model="quickEditForm.publishDate"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="分类">
          <el-tree-select
            v-model="quickEditForm.categoryId"
            :data="categoryTree"
            check-strictly
            clearable
            placeholder="选择分类"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="标签">
          <el-select
            v-model="quickEditForm.tags"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入标签后回车"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="重要度">
          <el-select v-model="quickEditForm.importance" style="width: 100%">
            <el-option v-for="o in IMPORTANCE_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="quickEditForm.status" style="width: 100%">
            <el-option v-for="s in ARTICLE_STATUSES" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="选项">
          <el-checkbox v-model="quickEditForm.isFeatured">置顶（重点必读）</el-checkbox>
          <el-checkbox v-model="quickEditForm.isDaily">今日推荐</el-checkbox>
          <el-checkbox v-model="quickEditForm.allowQuiz">允许答题</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="quickEditVisible = false">取消</el-button>
        <el-button type="primary" :loading="quickEditSaving" @click="submitQuickEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="articleImportVisible" title="导入 Markdown 长文" width="720px" destroy-on-close>
      <p class="import-hint">
        支持 <code>## 章</code> → <code>### 节</code> → <code>&gt; 引用块</code>（多段自动拆为「段」）。
        与移动端 level 1/2/3 一致。文档标题用 <code>#</code>。
      </p>
      <el-input
        v-model="articleImportMarkdown"
        type="textarea"
        :rows="18"
        placeholder="粘贴整篇 Markdown…"
      />
      <el-form label-width="96px" class="import-options">
        <el-form-item label="分类">
          <el-tree-select
            v-model="articleImportCategoryId"
            :data="categoryTree"
            check-strictly
            clearable
            placeholder="留空则自动识别"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="选项">
          <el-checkbox v-model="articleImportFeatured">标记为重点文章</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="articleImportVisible = false">取消</el-button>
        <el-button type="primary" :loading="articleImporting" @click="submitArticleImport">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  batchApproveArticles,
  batchDeleteArticles,
  batchRejectArticles,
  batchSetArticleCategory,
  fetchArticle,
  fetchArticles,
  importArticleMarkdown,
  updateArticle,
} from '@/api/articles'
import { fetchCategories } from '@/api/categories'
import ListState from '@/components/ListState.vue'
import { useAdminList } from '@/composables/useAdminList'
import { ARTICLE_STATUSES, IMPORTANCE_OPTIONS, type Article, type Category } from '@/types'

const router = useRouter()
const route = useRoute()
const { loading, loadError, runLoad } = useAdminList()
const batchLoading = ref(false)
const items = ref<Article[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const status = ref('')
const selectedRows = ref<Article[]>([])
const categories = ref<Category[]>([])
const categoryDialogVisible = ref(false)
const batchCategoryId = ref<string | null>(null)
const articleImportVisible = ref(false)
const articleImportMarkdown = ref('')
const articleImportCategoryId = ref<string | null>(null)
const articleImportFeatured = ref(false)
const articleImporting = ref(false)
const quickEditVisible = ref(false)
const quickEditSaving = ref(false)
const quickEditId = ref('')
const quickEditTitle = ref('')
const quickEditForm = ref({
  source: '',
  publishDate: '',
  categoryId: null as string | null,
  tags: [] as string[],
  importance: 3,
  status: 'published',
  isFeatured: false,
  isDaily: false,
  allowQuiz: true,
})

const selectedIds = computed(() => selectedRows.value.map((r) => r.id))
const categoryTree = computed(() => mapCategoryTree(categories.value))
const listEmptyText = computed(() =>
  keyword.value || status.value ? '没有符合条件的文章' : '暂无文章，点击「新建文章」开始',
)

function mapCategoryTree(list: Category[]): Array<{ value: string; label: string; children?: unknown[] }> {
  return list.map((c) => ({
    value: c.id,
    label: c.name,
    children: c.children?.length ? mapCategoryTree(c.children) : undefined,
  }))
}

function statusLabel(value?: string) {
  return ARTICLE_STATUSES.find((s) => s.value === value)?.label || value || '-'
}

function statusTagType(value?: string) {
  if (value === 'published') return 'success'
  if (value === 'pending') return 'warning'
  if (value === 'rejected') return 'danger'
  return 'info'
}

function onSelectionChange(rows: Article[]) {
  selectedRows.value = rows
}

async function load() {
  await runLoad(async () => {
    const data = await fetchArticles({
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value || undefined,
      status: status.value || undefined,
    })
    items.value = data.items
    total.value = data.total
  })
}

function filterPending() {
  status.value = 'pending'
  page.value = 1
  load()
}

function onPageSizeChange() {
  page.value = 1
  load()
}

async function onBatchApprove(approveQuestions: boolean) {
  const label = approveQuestions ? '发布并审核各文章下待审题目' : '仅发布文章'
  await ElMessageBox.confirm(`确定对 ${selectedIds.value.length} 篇文章${label}？`, '批量发布', { type: 'warning' })
  batchLoading.value = true
  try {
    const res = await batchApproveArticles(selectedIds.value, approveQuestions)
    ElMessage.success(
      approveQuestions && res.question_count
        ? `已发布 ${res.article_count} 篇，审核 ${res.question_count} 道题`
        : `已发布 ${res.article_count} 篇文章`,
    )
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '操作失败')
  } finally {
    batchLoading.value = false
  }
}

async function onBatchReject() {
  await ElMessageBox.confirm(`确定驳回 ${selectedIds.value.length} 篇文章？`, '批量驳回', { type: 'warning' })
  batchLoading.value = true
  try {
    const res = await batchRejectArticles(selectedIds.value)
    ElMessage.success(`已驳回 ${res.count} 篇文章`)
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '操作失败')
  } finally {
    batchLoading.value = false
  }
}

function openCategoryDialog() {
  batchCategoryId.value = null
  categoryDialogVisible.value = true
}

async function submitBatchCategory() {
  batchLoading.value = true
  try {
    const res = await batchSetArticleCategory(selectedIds.value, batchCategoryId.value)
    ElMessage.success(`已更新 ${res.count} 篇文章分类`)
    categoryDialogVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '操作失败')
  } finally {
    batchLoading.value = false
  }
}

async function onBatchDelete() {
  await ElMessageBox.confirm(`确定删除 ${selectedIds.value.length} 篇文章及其全部题目？`, '批量删除', { type: 'error' })
  batchLoading.value = true
  try {
    const res = await batchDeleteArticles(selectedIds.value)
    ElMessage.success(`已删除 ${res.count} 篇文章`)
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '操作失败')
  } finally {
    batchLoading.value = false
  }
}

function openArticleImportDialog() {
  articleImportMarkdown.value = ''
  articleImportCategoryId.value = null
  articleImportFeatured.value = false
  articleImportVisible.value = true
}

async function submitArticleImport() {
  if (!articleImportMarkdown.value.trim()) {
    ElMessage.warning('请粘贴 Markdown 内容')
    return
  }
  articleImporting.value = true
  try {
    const res = await importArticleMarkdown({
      markdown: articleImportMarkdown.value,
      status: 'pending',
      category_id: articleImportCategoryId.value,
      is_featured: articleImportFeatured.value,
    })
    articleImportVisible.value = false
    const stats = res.stats
    const warn = res.parse_warnings?.length ? `（${res.parse_warnings.length} 条提示）` : ''
    ElMessage.success(
      stats
        ? `已导入 ${stats.chapters} 章 ${stats.sections} 节 ${stats.paragraphs ?? 0} 段${warn}`
        : `导入成功${warn}`,
    )
    router.push(`/articles/${res.id}`)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '导入失败')
  } finally {
    articleImporting.value = false
  }
}

async function openQuickEdit(row: Article) {
  quickEditId.value = row.id
  quickEditTitle.value = row.title
  quickEditVisible.value = true
  quickEditSaving.value = false
  try {
    const detail = await fetchArticle(row.id)
    quickEditForm.value = {
      source: detail.source || '',
      publishDate: detail.publishDate || '',
      categoryId: detail.categoryId ?? null,
      tags: detail.tags ? [...detail.tags] : [],
      importance: detail.importance ?? 3,
      status: detail.status || 'published',
      isFeatured: !!detail.isFeatured,
      isDaily: !!detail.isDaily,
      allowQuiz: detail.allowQuiz !== false,
    }
  } catch {
    quickEditForm.value = {
      source: row.source || '',
      publishDate: row.publishDate || '',
      categoryId: row.categoryId ?? null,
      tags: row.tags ? [...row.tags] : [],
      importance: row.importance ?? 3,
      status: row.status || 'published',
      isFeatured: !!row.isFeatured,
      isDaily: !!row.isDaily,
      allowQuiz: row.allowQuiz !== false,
    }
  }
}

async function submitQuickEdit() {
  quickEditSaving.value = true
  try {
    await updateArticle(quickEditId.value, {
      source: quickEditForm.value.source,
      publish_date: quickEditForm.value.publishDate,
      category_id: quickEditForm.value.categoryId,
      tags: quickEditForm.value.tags,
      importance: quickEditForm.value.importance,
      status: quickEditForm.value.status,
      is_featured: quickEditForm.value.isFeatured,
      is_daily: quickEditForm.value.isDaily,
      allow_quiz: quickEditForm.value.allowQuiz,
    })
    ElMessage.success('已保存')
    quickEditVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    quickEditSaving.value = false
  }
}

onMounted(async () => {
  const q = route.query.status
  if (typeof q === 'string' && q) {
    status.value = q
  }
  categories.value = await fetchCategories()
  load()
})
watch(
  () => route.query.status,
  (q) => {
    if (typeof q === 'string') {
      status.value = q
      page.value = 1
      load()
    }
  },
)
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.batch-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  padding: 10px 12px;
  background: #ecf5ff;
  border-radius: 6px;
  font-size: 13px;
}
.pager { margin-top: 16px; justify-content: flex-end; }
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
.import-options {
  margin-top: 16px;
}
</style>
