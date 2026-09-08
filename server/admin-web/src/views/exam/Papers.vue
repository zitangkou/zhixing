<template>
  <div class="page">
    <div class="toolbar">
      <el-button type="primary" @click="openPaperDialog()">新建试卷</el-button>
      <el-button @click="load">刷新</el-button>
    </div>

    <el-alert type="info" :closable="false" style="margin-bottom: 12px">
      <div>支持 Markdown / JSON / CSV 三种格式导入题目。</div>
      <div>
        Markdown：## 模块 / ### 题号 / A. 选项 / &gt; **答案：B** / &gt; **解析：...**；
        资料分析请用 &gt; **材料** 多行块，并写 &gt; **知识点：比重** 等标签。
      </div>
      <div style="margin-top: 6px">
        资料分析导入规范：仓库
        <code>server/data/ziliao/IMPORT.md</code>
        ；可导入示例卷
        <code>server/data/ziliao/examples/guokao-style-sample.md</code>
        。有真题后，H5 练习池会自动排除系统样例卷。
      </div>
    </el-alert>

    <ListState
      :loading="loading"
      :error="loadError"
      :has-data="papers.length > 0"
      empty-text="暂无试卷，点击「新建试卷」开始"
      @retry="load"
    >
      <template #empty-action>
        <el-button type="primary" @click="openPaperDialog()">新建试卷</el-button>
      </template>
      <el-table :data="papers" v-loading="loading && papers.length > 0" row-key="id">
      <el-table-column prop="title" label="试卷名称" min-width="200" />
      <el-table-column label="类型" width="80">
        <template #default="{ row }">
          <el-tag :type="examTagType(row.examType)" size="small">{{ examTypeLabel(row.examType) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="subject" label="科目" width="80" />
      <el-table-column prop="year" label="年份" width="70" />
      <el-table-column prop="region" label="地区" width="80" />
      <el-table-column prop="totalCount" label="题数" width="70" />
      <el-table-column prop="timeLimitMin" label="时长(min)" width="90" />
      <el-table-column label="发布" width="70">
        <template #default="{ row }">
          <el-switch v-model="row.isPublished" @change="onTogglePublish(row)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240">
        <template #default="{ row }">
          <el-button link type="primary" @click="openImportDialog(row)">导入题目</el-button>
          <el-button link type="primary" @click="openPaperDialog(row)">编辑</el-button>
          <el-button link type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    </ListState>

    <!-- 试卷元信息对话框 -->
    <el-dialog v-model="paperVisible" :title="paperDialogTitle" width="540px">
      <el-form label-width="90px">
        <el-form-item label="试卷名称">
          <el-input v-model="paperForm.title" placeholder="如 2024 国考行测地市级" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="paperForm.examType">
            <el-option value="real" label="真题" />
            <el-option value="custom" label="自定义" />
            <el-option value="mock" label="模拟" />
          </el-select>
        </el-form-item>
        <el-form-item label="科目">
          <el-select v-model="paperForm.subject" allow-create filterable>
            <el-option value="行测" label="行测" />
            <el-option value="申论" label="申论" />
            <el-option value="公基" label="公基" />
          </el-select>
        </el-form-item>
        <el-form-item label="年份">
          <el-input-number v-model="paperForm.year" :min="2000" :max="2030" />
        </el-form-item>
        <el-form-item label="地区">
          <el-input v-model="paperForm.region" placeholder="国考 / 江苏 / 山东" />
        </el-form-item>
        <el-form-item label="级别">
          <el-input v-model="paperForm.level" placeholder="省级 / 地市级" />
        </el-form-item>
        <el-form-item label="限时(分)">
          <el-input-number v-model="paperForm.timeLimitMin" :min="10" :max="300" :step="10" />
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="paperForm.tags" multiple allow-create filterable default-first-option>
            <el-option value="行测" label="行测" />
            <el-option value="真题" label="真题" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="paperForm.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="发布">
          <el-switch v-model="paperForm.isPublished" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="paperVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="savePaper">保存</el-button>
      </template>
    </el-dialog>

    <!-- 导入题目对话框 -->
    <el-dialog v-model="importVisible" :title="`导入题目到「${importPaper?.title}」`" width="640px">
      <el-tabs v-model="importTab">
        <el-tab-pane label="上传文件" name="upload">
          <el-upload
            :show-file-list="false"
            :before-upload="onBeforeUpload"
            :http-request="onUploadFile"
            accept=".md,.json,.csv,.txt"
          >
            <el-button type="primary" :loading="uploading">选择文件 (.md / .json / .csv / .txt)</el-button>
          </el-upload>
          <div v-if="preview" class="preview-box">
            <div class="preview-head">
              <span>解析成功 {{ preview.parsed }} 题</span>
              <span v-if="preview.errors.length" class="preview-err">{{ preview.errors.length }} 条错误</span>
            </div>
            <div v-if="preview.errors.length" class="preview-errors">
              <div v-for="(e, i) in preview.errors.slice(0, 5)" :key="i" class="err-line">{{ e }}</div>
            </div>
            <div class="preview-list">
              <div v-for="(q, i) in preview.preview" :key="i" class="preview-item">
                <div class="pi-head">
                  <span>{{ q.section || '未分类' }} #{{ q.section_index }}</span>
                  <span class="pi-type">{{ q.type }}</span>
                </div>
                <div class="pi-stem">{{ q.stem }}</div>
                <div class="pi-ans">答案：{{ formatAns(q.correct_answer) }}</div>
              </div>
            </div>
          </div>
        </el-tab-pane>
        <el-tab-pane label="粘贴文本" name="paste">
          <el-input
            v-model="pasteContent"
            type="textarea"
            :rows="10"
            placeholder="粘贴 Markdown / JSON / CSV 内容..."
          />
          <div style="margin-top: 10px; display: flex; gap: 8px;">
            <el-input v-model="pasteFileName" placeholder="文件名（用于识别格式，如 exam.json）" style="width: 240px" />
            <el-button @click="onPastePreview" :loading="uploading">预览</el-button>
          </div>
          <div v-if="preview" class="preview-box">
            <div class="preview-head">
              <span>解析成功 {{ preview.parsed }} 题</span>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" :disabled="!preview || preview.parsed === 0" @click="onConfirmImport">
          确认导入 {{ preview?.parsed || 0 }} 题
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createExamPaper,
  deleteExamPaper,
  fetchExamPapers,
  importConfirm,
  importPreview,
  updateExamPaper,
  uploadExamFile,
  type ExamImportPreview,
  type ExamPaper,
} from '@/api/exam'
import ListState from '@/components/ListState.vue'
import { useAdminList } from '@/composables/useAdminList'

const { loading, loadError, runLoad } = useAdminList()
const saving = ref(false)
const uploading = ref(false)
const importing = ref(false)
const papers = ref<ExamPaper[]>([])
const paperVisible = ref(false)
const editPaperId = ref<string | null>(null)
const paperForm = reactive({
  title: '',
  examType: 'real' as 'real' | 'custom' | 'mock',
  subject: '行测',
  year: null as number | null,
  region: '',
  level: '',
  timeLimitMin: 120,
  tags: [] as string[],
  isPublished: true,
  isFree: true,
  sortOrder: 0,
  description: '',
})

const importVisible = ref(false)
const importPaper = ref<ExamPaper | null>(null)
const importTab = ref('upload')
const preview = ref<ExamImportPreview | null>(null)
const pasteContent = ref('')
const pasteFileName = ref('exam.md')

const paperDialogTitle = computed(() => (editPaperId.value ? '编辑试卷' : '新建试卷'))

function examTypeLabel(t: string) {
  return { real: '真题', custom: '自定义', mock: '模拟' }[t] || t
}
function examTagType(t: string): any {
  return { real: 'danger', custom: '', mock: 'success' }[t] || ''
}
function formatAns(a: any) {
  if (Array.isArray(a)) return a.join('、')
  return a || ''
}

async function load() {
  await runLoad(async () => {
    papers.value = await fetchExamPapers()
  })
}

function openPaperDialog(row?: ExamPaper) {
  if (row) {
    editPaperId.value = row.id
    paperForm.title = row.title
    paperForm.examType = row.examType
    paperForm.subject = row.subject
    paperForm.year = row.year
    paperForm.region = row.region
    paperForm.level = row.level
    paperForm.timeLimitMin = row.timeLimitMin
    paperForm.tags = [...row.tags]
    paperForm.isPublished = row.isPublished
    paperForm.isFree = row.isFree
    paperForm.sortOrder = row.sortOrder
    paperForm.description = row.description
  } else {
    editPaperId.value = null
    paperForm.title = ''
    paperForm.examType = 'real'
    paperForm.subject = '行测'
    paperForm.year = null
    paperForm.region = ''
    paperForm.level = ''
    paperForm.timeLimitMin = 120
    paperForm.tags = []
    paperForm.isPublished = true
    paperForm.isFree = true
    paperForm.sortOrder = 0
    paperForm.description = ''
  }
  paperVisible.value = true
}

async function savePaper() {
  if (!paperForm.title.trim()) {
    ElMessage.warning('请输入试卷名称')
    return
  }
  saving.value = true
  try {
    const data = {
      title: paperForm.title.trim(),
      examType: paperForm.examType,
      subject: paperForm.subject,
      year: paperForm.year,
      region: paperForm.region,
      level: paperForm.level,
      timeLimitMin: paperForm.timeLimitMin,
      tags: paperForm.tags,
      isPublished: paperForm.isPublished,
      isFree: paperForm.isFree,
      sortOrder: paperForm.sortOrder,
      description: paperForm.description,
    }
    if (editPaperId.value) {
      await updateExamPaper(editPaperId.value, data)
      ElMessage.success('已保存')
    } else {
      await createExamPaper(data)
      ElMessage.success('已创建')
    }
    paperVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function onTogglePublish(row: ExamPaper) {
  try {
    await updateExamPaper(row.id, { isPublished: row.isPublished })
    ElMessage.success(row.isPublished ? '已发布' : '已下架')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '操作失败')
    row.isPublished = !row.isPublished
  }
}

async function onDelete(row: ExamPaper) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.title}」？该卷所有题目和作答记录会一并删除`, '危险操作', { type: 'error' })
    await deleteExamPaper(row.id)
    await load()
    ElMessage.success('已删除')
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e instanceof Error ? e.message : '删除失败')
    }
  }
}

// ===== 导入题目 =====

function openImportDialog(row: ExamPaper) {
  importPaper.value = row
  preview.value = null
  pasteContent.value = ''
  pasteFileName.value = 'exam.md'
  importTab.value = 'upload'
  importVisible.value = true
}

function onBeforeUpload(file: File) {
  const ok = ['.md', '.json', '.csv', '.txt'].some((ext) => file.name.toLowerCase().endsWith(ext))
  if (!ok) {
    ElMessage.warning('仅支持 .md / .json / .csv / .txt')
    return false
  }
  if (file.size > 2 * 1024 * 1024) {
    ElMessage.warning('文件不能超过 2MB')
    return false
  }
  return true
}

async function onUploadFile(options: { file: File }) {
  uploading.value = true
  try {
    preview.value = await uploadExamFile(options.file)
    if (preview.value.errors.length) {
      ElMessage.warning(`解析成功 ${preview.value.parsed} 题，${preview.value.errors.length} 条错误`)
    } else {
      ElMessage.success(`解析成功 ${preview.value.parsed} 题`)
    }
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '上传失败')
  } finally {
    uploading.value = false
  }
}

async function onPastePreview() {
  if (!pasteContent.value.trim() || !importPaper.value) return
  uploading.value = true
  try {
    preview.value = await importPreview(
      importPaper.value.id,
      pasteFileName.value || 'exam.md',
      pasteContent.value,
    ) as ExamImportPreview
    if (preview.value.errors.length) {
      ElMessage.warning(`解析 ${preview.value.parsed} 题，${preview.value.errors.length} 错误`)
    } else {
      ElMessage.success(`解析 ${preview.value.parsed} 题`)
    }
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '解析失败')
  } finally {
    uploading.value = false
  }
}

async function onConfirmImport() {
  if (!importPaper.value || !preview.value) return
  importing.value = true
  try {
    // 用上传文件的 questions 或粘贴的 content
    if (preview.value.questions && preview.value.questions.length) {
      // 来自上传接口：直接用 content 重新提交（避免再传文件）
      // 实际上 uploadExamFile 返回了 questions，但 confirm 接口需要 content
      // 这里复用 preview.questions 转 JSON 字符串提交
      const content = JSON.stringify(preview.value.questions)
      const r = await importConfirm(importPaper.value.id, 'exam.json', content)
      ElMessage.success(`已导入 ${r.inserted} 题`)
    } else if (pasteContent.value) {
      const r = await importConfirm(importPaper.value.id, pasteFileName.value, pasteContent.value)
      ElMessage.success(`已导入 ${r.inserted} 题`)
    }
    importVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '导入失败')
  } finally {
    importing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.preview-box { margin-top: 12px; padding: 10px; background: #f7f7f7; border-radius: 6px; }
.preview-head { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; }
.preview-err { color: #ee0a24; }
.preview-errors { background: #fff0f0; padding: 8px; border-radius: 4px; margin-bottom: 8px; }
.err-line { font-size: 12px; color: #c00; margin: 2px 0; }
.preview-list { max-height: 200px; overflow-y: auto; }
.preview-item { background: #fff; padding: 8px; border-radius: 4px; margin-bottom: 6px; font-size: 12px; }
.pi-head { display: flex; justify-content: space-between; color: #888; margin-bottom: 4px; }
.pi-type { color: #1E3A5F; }
.pi-stem { color: #333; margin-bottom: 4px; }
.pi-ans { color: #07c160; }
</style>
