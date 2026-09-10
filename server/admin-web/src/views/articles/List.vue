<template>
  <div class="page">
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索标题" clearable style="width: 240px" @keyup.enter="load" />
      <el-select v-model="status" placeholder="状态" clearable style="width: 140px" @change="load">
        <el-option v-for="s in ARTICLE_STATUSES" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button type="primary" @click="openArticleImportDialog">新建文章</el-button>
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
    </div>

    <ListState
      :loading="loading"
      :error="loadError"
      :has-data="items.length > 0"
      :empty-text="listEmptyText"
      @retry="load"
    >
      <template #empty-action>
        <el-button type="primary" @click="openArticleImportDialog">新建文章</el-button>
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
      <el-table-column label="正文" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.contentHtml" size="small" type="success">HTML</el-tag>
          <el-tag v-else size="small" type="info">结构化</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="标记" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.isDaily" size="small" type="danger">今日</el-tag>
          <span v-else style="color: #999">—</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="router.push(`/articles/${row.id}`)">编辑</el-button>
          <el-button link type="primary" @click="openQuickEdit(row)">快速编辑</el-button>
          <el-button link type="danger" @click="onDelete(row)">删除</el-button>
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

    <el-dialog v-model="articleImportVisible" title="新建文章" width="720px" destroy-on-close>
      <p class="import-hint">先核对来源等信息，再粘贴运营结构化 HTML。点预览会从引导卡回填上方字段。</p>
      <el-form label-width="96px" class="import-options">
        <el-form-item label="来源">
          <el-input v-model="articleImportSource" placeholder="预览可从「来源：」带出" />
        </el-form-item>
        <el-form-item label="发布日期">
          <el-input v-model="articleImportPublishDate" placeholder="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="原文链接">
          <el-input v-model="articleImportSourceUrl" placeholder="预览可从原文链接带出" />
        </el-form-item>
        <el-form-item label="摘要">
          <el-input v-model="articleImportSummary" type="textarea" :rows="2" placeholder="可空，预览时从正文抽取" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="articleImportTagsText" placeholder="逗号分隔" />
        </el-form-item>
        <el-form-item label="分类">
          <el-tree-select
            v-model="articleImportCategoryId"
            :data="categoryTree"
            check-strictly
            clearable
            placeholder="留空则导入时自动识别"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="选项">
          <el-checkbox v-model="articleImportFeatured">标记为重点文章</el-checkbox>
          <el-checkbox v-model="articleImportDaily">今日推荐</el-checkbox>
        </el-form-item>
        <el-form-item label="正文 HTML">
          <el-input
            v-model="articleImportBody"
            type="textarea"
            :rows="12"
            placeholder="粘贴完整 HTML…"
          />
        </el-form-item>
      </el-form>
      <div class="import-preview-bar">
        <el-button :loading="articlePreviewing" @click="previewArticleImport">预览</el-button>
        <span v-if="articleImportPreview" class="import-preview-stats">
          {{ articleImportPreview.title }} · {{ articleImportPreview.stats.chars ?? 0 }} 字
        </span>
      </div>
      <ul v-if="articleImportPreview?.parse_warnings?.length" class="import-warnings">
        <li v-for="(w, i) in articleImportPreview.parse_warnings" :key="i">{{ w }}</li>
      </ul>
      <template #footer>
        <el-button @click="articleImportVisible = false">取消</el-button>
        <el-button type="primary" :loading="articleImporting" @click="submitArticleImport">确定</el-button>
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
  batchRejectArticles,
  batchSetArticleCategory,
  deleteArticle,
  fetchArticle,
  fetchArticles,
  importArticleHtml,
  previewArticleHtml,
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
const articleImportBody = ref('')
const articleImportCategoryId = ref<string | null>(null)
const articleImportFeatured = ref(false)
const articleImportDaily = ref(false)
const articleImportSource = ref('')
const articleImportPublishDate = ref('')
const articleImportSourceUrl = ref('')
const articleImportSummary = ref('')
const articleImportTagsText = ref('')
const articleImporting = ref(false)
const articlePreviewing = ref(false)
const articleImportPreview = ref<{
  title: string
  source?: string
  publishDate?: string
  sourceUrl?: string
  summary?: string
  tags?: string[]
  categoryName?: string
  stats: { chapters: number; sections: number; paragraphs: number; chars?: number }
  parse_warnings: string[]
} | null>(null)
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

function findCategoryId(list: Category[], name: string): string | null {
  const target = name.trim()
  if (!target) return null
  for (const node of list) {
    if (node.name === target) return node.id
    const nested = node.children?.length ? findCategoryId(node.children, target) : null
    if (nested) return nested
  }
  return null
}

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

async function onDelete(row: Article) {
  await ElMessageBox.confirm(`确定删除「${row.title}」及其全部题目？`, '删除文章', { type: 'error' })
  try {
    await deleteArticle(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '删除失败')
  }
}

function openArticleImportDialog() {
  articleImportBody.value = ''
  articleImportCategoryId.value = null
  articleImportFeatured.value = false
  articleImportDaily.value = false
  articleImportSource.value = ''
  articleImportPublishDate.value = ''
  articleImportSourceUrl.value = ''
  articleImportSummary.value = ''
  articleImportTagsText.value = ''
  articleImportPreview.value = null
  articleImportVisible.value = true
}

async function previewArticleImport() {
  if (!articleImportBody.value.trim()) {
    ElMessage.warning('请粘贴 HTML')
    return
  }
  articlePreviewing.value = true
  try {
    const preview = await previewArticleHtml(articleImportBody.value)
    articleImportPreview.value = preview
    articleImportSource.value = preview.source || ''
    articleImportPublishDate.value = preview.publishDate || ''
    articleImportSourceUrl.value = preview.sourceUrl || ''
    articleImportSummary.value = preview.summary || ''
    articleImportTagsText.value = (preview.tags || []).join('，')
    if (preview.categoryName) {
      articleImportCategoryId.value = findCategoryId(categories.value, preview.categoryName)
    }
    ElMessage.success(`解析到「${preview.title}」`)
  } catch (e) {
    articleImportPreview.value = null
    ElMessage.error(e instanceof Error ? e.message : '预览失败')
  } finally {
    articlePreviewing.value = false
  }
}

async function submitArticleImport() {
  if (!articleImportBody.value.trim()) {
    ElMessage.warning('请粘贴 HTML 内容')
    return
  }
  articleImporting.value = true
  try {
    const res = await importArticleHtml({
      html: articleImportBody.value,
      status: 'pending',
      category_id: articleImportCategoryId.value,
      is_featured: articleImportFeatured.value,
      is_daily: articleImportDaily.value,
      source: articleImportSource.value,
      source_url: articleImportSourceUrl.value,
      publish_date: articleImportPublishDate.value,
      summary: articleImportSummary.value.trim(),
      tags: articleImportTagsText.value.split(/[,，]/).map((s) => s.trim()).filter(Boolean),
    })
    articleImportVisible.value = false
    const warn = res.parse_warnings?.length ? `（${res.parse_warnings.length} 条提示）` : ''
    ElMessage.success(`已创建文章${warn}`)
    router.push(`/articles/${res.id}`)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '创建失败')
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
  margin-top: 0;
}
.import-preview-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 10px 0 8px;
  flex-wrap: wrap;
}
.import-preview-stats {
  font-size: 13px;
  color: #606266;
}
.import-warnings {
  margin: 0 0 8px;
  padding-left: 18px;
  color: #e6a23c;
  font-size: 12px;
  line-height: 1.5;
  max-height: 96px;
  overflow: auto;
}
</style>
