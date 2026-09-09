<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openDialog()">新建时评</el-button>
      <el-button @click="load">刷新</el-button>
      <el-select
        v-model="filterTag"
        clearable
        placeholder="按主题筛选"
        style="width: 180px; margin-left: auto"
        @change="load"
      >
        <el-option v-for="t in themePresets" :key="t" :label="t" :value="t" />
      </el-select>
    </div>
    <el-alert type="info" :closable="false" style="margin-bottom: 12px">
      先贴原文 HTML 保存，再点「导入解析」贴精拆 HTML。标题等字段会从原文 HTML 自动抽取。
    </el-alert>

    <ListState
      :loading="loading"
      :error="loadError"
      :has-data="articles.length > 0"
      :empty-text="filterTag ? '该主题下暂无时评' : '暂无时评，点击「新建时评」开始'"
      @retry="load"
    >
      <template #empty-action>
        <el-button type="primary" @click="openDialog()">新建时评</el-button>
      </template>
      <el-table :data="articles" v-loading="loading && articles.length > 0" row-key="id">
      <el-table-column prop="title" label="标题" min-width="200" />
      <el-table-column prop="source" label="来源" width="100" />
      <el-table-column prop="publishDate" label="日期" width="110" />
      <el-table-column label="标记" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.isDaily" size="small" type="danger">今日</el-tag>
          <span v-else style="color: #999">—</span>
        </template>
      </el-table-column>
      <el-table-column label="主题" min-width="160">
        <template #default="{ row }">
          <el-tag v-for="t in row.tags || []" :key="t" size="small" style="margin: 2px 4px 2px 0">{{ t }}</el-tag>
          <span v-if="!(row.tags && row.tags.length)" style="color: #999">—</span>
        </template>
      </el-table-column>
      <el-table-column label="解析" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.hasParse" size="small" type="success">已挂</el-tag>
          <span v-else style="color: #999">无</span>
        </template>
      </el-table-column>
      <el-table-column prop="readCount" label="阅读" width="70" />
      <el-table-column label="发布" width="70">
        <template #default="{ row }">
          <el-switch v-model="row.isPublished" @change="onToggle(row)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑原文</el-button>
          <el-button link type="primary" @click="openImport(row)">导入解析</el-button>
          <el-button link type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    </ListState>

    <el-dialog v-model="visible" :title="editId ? '编辑时评' : '新建时评'" width="720px">
      <el-form label-width="90px">
        <el-form-item label="原文 HTML" required>
          <el-input
            v-model="form.contentHtml"
            type="textarea"
            :rows="14"
            placeholder="粘贴时评原文 HTML"
          />
        </el-form-item>
        <el-form-item label="摘要">
          <el-input v-model="form.summary" type="textarea" :rows="2" placeholder="可空，空则从 HTML 抽取" />
        </el-form-item>
        <el-form-item label="主题">
          <el-select
            v-model="form.tags"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="选择或输入主题"
            style="width: 100%"
          >
            <el-option v-for="t in themeOptions" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="来源">
          <el-input v-model="form.source" placeholder="可空，空则从 HTML 抽取" />
        </el-form-item>
        <el-form-item label="发布日期">
          <el-input v-model="form.publishDate" placeholder="YYYY-MM-DD，可空" />
        </el-form-item>
        <el-form-item label="原文链接">
          <el-input v-model="form.sourceUrl" placeholder="可空" />
        </el-form-item>
        <el-form-item label="今日推荐">
          <el-checkbox v-model="form.isDaily">作为学员端「今日时评」</el-checkbox>
        </el-form-item>
        <el-form-item label="发布">
          <el-switch v-model="form.isPublished" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="importVisible"
      :title="importTarget ? `导入解析 · ${importTarget.title}` : '导入解析'"
      width="720px"
      destroy-on-close
    >
      <ThreeKnifeImportTab
        v-if="importTarget"
        :key="importTarget.id"
        :article-id="importTarget.id"
        :article-title="importTarget.title"
        @imported="onImported"
      />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createRmrbArticle,
  deleteRmrbArticle,
  fetchRmrbArticles,
  updateRmrbArticle,
  type RmrbArticle,
} from '@/api/rmrb'
import ListState from '@/components/ListState.vue'
import { useAdminList } from '@/composables/useAdminList'
import ThreeKnifeImportTab from './ThreeKnifeImportTab.vue'

/** 常用主题预设，也可在下拉里自建 */
const themePresets = [
  '政绩观',
  '社会治理',
  '乡村振兴',
  '县域经济',
  '高质量发展',
  '民生保障',
  '作风建设',
  '基层减负',
  '科技创新',
  '文化建设',
  '生态文明',
  '依法治国',
]

const { loading, loadError, runLoad } = useAdminList()
const saving = ref(false)
const articles = ref<RmrbArticle[]>([])
const visible = ref(false)
const importVisible = ref(false)
const importTarget = ref<RmrbArticle | null>(null)
const editId = ref<string | null>(null)
const filterTag = ref('')
const form = reactive({
  contentHtml: '',
  summary: '',
  tags: [] as string[],
  source: '',
  publishDate: '',
  sourceUrl: '',
  isPublished: true,
  isDaily: false,
})

const themeOptions = computed(() => {
  const extra = form.tags.filter((t) => t && !themePresets.includes(t))
  return [...themePresets, ...extra]
})

async function load() {
  await runLoad(async () => {
    articles.value = await fetchRmrbArticles(filterTag.value || undefined)
  })
}

function resetForm() {
  form.contentHtml = ''
  form.summary = ''
  form.tags = []
  form.source = ''
  form.publishDate = ''
  form.sourceUrl = ''
  form.isPublished = true
  form.isDaily = false
}

function openDialog(row?: RmrbArticle) {
  if (row) {
    editId.value = row.id
    form.contentHtml = row.contentHtml || ''
    form.summary = row.summary || ''
    form.tags = [...(row.tags || [])]
    form.source = row.source || ''
    form.publishDate = row.publishDate || ''
    form.sourceUrl = row.sourceUrl || ''
    form.isPublished = row.isPublished
    form.isDaily = !!row.isDaily
  } else {
    editId.value = null
    resetForm()
  }
  visible.value = true
}

function openImport(row: RmrbArticle) {
  importTarget.value = row
  importVisible.value = true
}

function onImported() {
  importVisible.value = false
  importTarget.value = null
  load()
}

async function save() {
  if (!form.contentHtml.trim()) {
    ElMessage.warning('请粘贴原文 HTML')
    return
  }
  saving.value = true
  const payload = {
    contentHtml: form.contentHtml,
    summary: form.summary.trim(),
    tags: form.tags,
    source: form.source.trim(),
    publishDate: form.publishDate.trim(),
    sourceUrl: form.sourceUrl.trim(),
    isDaily: form.isDaily,
    isPublished: form.isPublished,
  }
  try {
    if (editId.value) {
      await updateRmrbArticle(editId.value, payload)
      ElMessage.success('原文已保存')
      visible.value = false
      await load()
    } else {
      const created = await createRmrbArticle(payload)
      ElMessage.success('原文已保存')
      visible.value = false
      await load()
      try {
        await ElMessageBox.confirm('是否继续导入解析 HTML？', '原文已就绪', {
          type: 'info',
          confirmButtonText: '导入解析',
          cancelButtonText: '稍后再说',
        })
        openImport(created)
      } catch {
        /* 用户取消 */
      }
    }
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function onToggle(row: RmrbArticle) {
  try {
    await updateRmrbArticle(row.id, { isPublished: row.isPublished })
  } catch {
    row.isPublished = !row.isPublished
  }
}

async function onDelete(row: RmrbArticle) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.title}」？`, '提示', { type: 'warning' })
    await deleteRmrbArticle(row.id)
    await load()
    ElMessage.success('已删除')
    } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e instanceof Error ? e.message : '删除失败')
    }
  }
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}
</style>
