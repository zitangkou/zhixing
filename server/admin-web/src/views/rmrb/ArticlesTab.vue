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
      仅服务「人民日报」学习模块。建议为每篇打上主题标签（政绩观、乡村振兴等），便于日后归类总结。
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
      <el-table-column label="主题" min-width="160">
        <template #default="{ row }">
          <el-tag v-for="t in row.tags || []" :key="t" size="small" style="margin: 2px 4px 2px 0">{{ t }}</el-tag>
          <span v-if="!(row.tags && row.tags.length)" style="color: #999">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="readCount" label="阅读" width="70" />
      <el-table-column label="发布" width="70">
        <template #default="{ row }">
          <el-switch v-model="row.isPublished" @change="onToggle(row)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button link type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    </ListState>

    <el-dialog v-model="visible" :title="editId ? '编辑时评' : '新建时评'" width="720px">
      <el-form label-width="90px">
        <el-form-item label="标题">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="来源">
          <el-select v-model="form.source" allow-create filterable>
            <el-option value="人民时评" label="人民时评" />
            <el-option value="评论" label="评论" />
            <el-option value="任仲平" label="任仲平" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期">
          <el-input v-model="form.publishDate" placeholder="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="原文链接">
          <el-input v-model="form.sourceUrl" placeholder="https://paper.people.com.cn/..." />
        </el-form-item>
        <el-form-item label="主题标签">
          <el-select
            v-model="form.tags"
            multiple
            allow-create
            filterable
            default-first-option
            placeholder="选择或输入主题，如政绩观"
            style="width: 100%"
          >
            <el-option v-for="t in themePresets" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="摘要">
          <el-input v-model="form.summary" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="正文">
          <el-input v-model="form.content" type="textarea" :rows="12" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sortOrder" :min="0" />
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
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
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
const editId = ref<string | null>(null)
const filterTag = ref('')
const form = reactive({
  title: '',
  source: '人民时评',
  sourceUrl: '',
  publishDate: '',
  summary: '',
  content: '',
  tags: [] as string[],
  sortOrder: 0,
  isPublished: true,
})

async function load() {
  await runLoad(async () => {
    articles.value = await fetchRmrbArticles(filterTag.value || undefined)
  })
}

function openDialog(row?: RmrbArticle) {
  if (row) {
    editId.value = row.id
    form.title = row.title
    form.source = row.source
    form.sourceUrl = row.sourceUrl || ''
    form.publishDate = row.publishDate
    form.summary = row.summary
    form.content = row.content
    form.tags = [...(row.tags || [])]
    form.sortOrder = row.sortOrder
    form.isPublished = row.isPublished
  } else {
    editId.value = null
    form.title = ''
    form.source = '人民时评'
    form.sourceUrl = ''
    form.publishDate = new Date().toISOString().slice(0, 10)
    form.summary = ''
    form.content = ''
    form.tags = []
    form.sortOrder = 0
    form.isPublished = true
  }
  visible.value = true
}

async function save() {
  if (!form.title.trim()) {
    ElMessage.warning('请输入标题')
    return
  }
  saving.value = true
  try {
    if (editId.value) {
      await updateRmrbArticle(editId.value, { ...form })
      ElMessage.success('已保存')
    } else {
      await createRmrbArticle({ ...form })
      ElMessage.success('已创建')
    }
    visible.value = false
    await load()
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
    if (e !== 'cancel' && e !== 'close') ElMessage.error('删除失败')
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
