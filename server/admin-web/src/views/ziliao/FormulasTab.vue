<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openDialog()">新建公式</el-button>
      <el-button @click="openImportDialog">导入 JSON</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="rows" v-loading="loading" row-key="id">
      <el-table-column prop="code" label="编码" width="90" />
      <el-table-column prop="name" label="名称" min-width="100" />
      <el-table-column prop="category" label="分类" width="80" />
      <el-table-column label="公式预览" min-width="200">
        <template #default="{ row }">
          <div class="preview-cell" v-html="previewHtml(row.latex)" />
          <div class="plain-cell">{{ row.formulaPlain || '—' }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="examFreq" label="频率" width="70" />
      <el-table-column prop="sortOrder" label="排序" width="70" />
      <el-table-column label="发布" width="70">
        <template #default="{ row }">
          <el-switch v-model="row.isPublished" @change="onToggle(row)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button link type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="editId ? '编辑公式' : '新建公式'" width="720px">
      <el-form label-width="100px">
        <el-form-item label="编码"><el-input v-model="form.code" :disabled="!!editId" /></el-form-item>
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="分类"><el-input v-model="form.category" /></el-form-item>
        <el-form-item label="定义"><el-input v-model="form.definition" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="LaTeX">
          <el-input
            v-model="form.latex"
            type="textarea"
            :rows="2"
            placeholder="如 r=\dfrac{A_{1}-A_{0}}{A_{0}}"
          />
        </el-form-item>
        <el-form-item label="预览">
          <div class="preview-box" v-html="previewHtml(form.latex)" />
        </el-form-item>
        <el-form-item label="中文式">
          <el-input
            v-model="form.formulaPlain"
            placeholder="增长率 = (现期 − 基期) / 基期"
          />
        </el-form-item>
        <el-form-item label="场景"><el-input v-model="form.scenarios" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="易错"><el-input v-model="form.pitfalls" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="频率"><el-input-number v-model="form.examFreq" :min="1" :max="5" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sortOrder" :min="0" /></el-form-item>
        <el-form-item label="发布"><el-switch v-model="form.isPublished" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importVisible" title="导入公式 JSON" width="720px">
      <el-alert
        type="info"
        show-icon
        :closable="false"
        title="按 code 匹配公式：已存在则更新，不存在则新增。JSON 可为数组，也可为 { formulas: [...] }。"
      />
      <div class="import-options">
        <el-checkbox v-model="importOverwrite">覆盖同编码公式</el-checkbox>
        <el-checkbox v-model="importPublishDefault">未声明发布状态时默认发布</el-checkbox>
      </div>
      <el-tabs v-model="importTab">
        <el-tab-pane label="上传文件" name="upload">
          <el-upload
            :show-file-list="false"
            :before-upload="onBeforeImportUpload"
            :http-request="onUploadImportFile"
            accept=".json"
          >
            <el-button type="primary" :loading="importing">选择 JSON 文件</el-button>
          </el-upload>
        </el-tab-pane>
        <el-tab-pane label="粘贴 JSON" name="paste">
          <el-input
            v-model="importContent"
            type="textarea"
            :rows="14"
            :placeholder="importPlaceholder"
          />
        </el-tab-pane>
      </el-tabs>
      <div v-if="importResult" class="import-result">
        <div>
          共 {{ importResult.total }} 条，新增 {{ importResult.inserted }} 条，更新 {{ importResult.updated }} 条，跳过 {{ importResult.skipped }} 条
        </div>
        <div v-if="importResult.errors.length" class="import-errors">
          <div v-for="(err, i) in importResult.errors.slice(0, 8)" :key="i">{{ err }}</div>
        </div>
      </div>
      <template #footer>
        <el-button @click="importVisible = false">关闭</el-button>
        <el-button
          v-if="importTab === 'paste'"
          type="primary"
          :loading="importing"
          :disabled="!importContent.trim()"
          @click="submitImportJson"
        >
          导入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import {
  createFormula,
  deleteFormula,
  importFormulasJson,
  listFormulas,
  updateFormula,
  uploadFormulasJson,
  type ZiliaoFormula,
  type ZiliaoFormulaImportResult,
} from '@/api/ziliao'

const rows = ref<ZiliaoFormula[]>([])
const loading = ref(false)
const visible = ref(false)
const saving = ref(false)
const importing = ref(false)
const editId = ref('')
const importVisible = ref(false)
const importTab = ref('upload')
const importContent = ref('')
const importOverwrite = ref(true)
const importPublishDefault = ref(true)
const importResult = ref<ZiliaoFormulaImportResult | null>(null)
const form = reactive({
  code: '',
  name: '',
  category: '',
  definition: '',
  latex: '',
  formulaPlain: '',
  scenarios: '',
  pitfalls: '',
  examFreq: 3,
  sortOrder: 0,
  isPublished: true,
})
const importPlaceholder = `[
  {
    "code": "F001",
    "name": "增长率",
    "category": "增长",
    "definition": "反映现期相对基期的增长快慢。",
    "latex": "r=\\\\dfrac{A_{1}-A_{0}}{A_{0}}",
    "formulaPlain": "增长率 = (现期 − 基期) / 基期",
    "scenarios": "同比增长多少、增幅是多少、增长率是多少",
    "pitfalls": "分母是基期不是现期；注意百分数与百分点区别",
    "related_type_codes": ["T001", "T002"],
    "related_trick_codes": ["K001"],
    "keywords": ["增长率", "同比"],
    "exam_freq": 5,
    "sort_order": 1,
    "is_published": true
  }
]`

function previewHtml(tex: string) {
  const src = (tex || '').trim()
  if (!src) return '<span style="color:#999">输入 LaTeX 后预览</span>'
  try {
    return katex.renderToString(src, {
      throwOnError: false,
      strict: 'ignore',
      displayMode: true,
    })
  } catch {
    return `<code>${src}</code>`
  }
}

async function load() {
  loading.value = true
  try {
    rows.value = await listFormulas()
  } finally {
    loading.value = false
  }
}

function openDialog(row?: ZiliaoFormula) {
  editId.value = row?.id || ''
  Object.assign(form, {
    code: row?.code || '',
    name: row?.name || '',
    category: row?.category || '',
    definition: row?.definition || '',
    latex: row?.latex || '',
    formulaPlain: row?.formulaPlain || '',
    scenarios: row?.scenarios || '',
    pitfalls: row?.pitfalls || '',
    examFreq: row?.examFreq ?? 3,
    sortOrder: row?.sortOrder ?? 0,
    isPublished: row?.isPublished ?? true,
  })
  visible.value = true
}

async function save() {
  saving.value = true
  try {
    if (editId.value) await updateFormula(editId.value, { ...form })
    else await createFormula({ ...form })
    visible.value = false
    ElMessage.success('已保存')
    await load()
  } finally {
    saving.value = false
  }
}

function openImportDialog() {
  importVisible.value = true
  importTab.value = 'upload'
  importContent.value = ''
  importResult.value = null
  importOverwrite.value = true
  importPublishDefault.value = true
}

function onBeforeImportUpload(file: File) {
  if (!file.name.toLowerCase().endsWith('.json')) {
    ElMessage.warning('仅支持 .json 文件')
    return false
  }
  if (file.size > 2 * 1024 * 1024) {
    ElMessage.warning('文件不能超过 2MB')
    return false
  }
  return true
}

function showImportResult(result: ZiliaoFormulaImportResult) {
  importResult.value = result
  const msg = `新增 ${result.inserted} 条，更新 ${result.updated} 条，跳过 ${result.skipped} 条`
  if (result.errors.length) ElMessage.warning(`${msg}，${result.errors.length} 条错误`)
  else ElMessage.success(msg)
}

async function onUploadImportFile(options: { file: File }) {
  importing.value = true
  try {
    const result = await uploadFormulasJson(options.file, importOverwrite.value, importPublishDefault.value)
    showImportResult(result)
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '导入失败')
  } finally {
    importing.value = false
  }
}

async function submitImportJson() {
  if (!importContent.value.trim()) return
  importing.value = true
  try {
    const result = await importFormulasJson({
      content: importContent.value,
      overwrite: importOverwrite.value,
      publishDefault: importPublishDefault.value,
    })
    showImportResult(result)
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '导入失败')
  } finally {
    importing.value = false
  }
}

async function onToggle(row: ZiliaoFormula) {
  await updateFormula(row.id, { isPublished: row.isPublished })
}

async function onDelete(row: ZiliaoFormula) {
  await ElMessageBox.confirm(`删除公式「${row.name}」？`)
  await deleteFormula(row.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.preview-cell :deep(.katex) {
  font-size: 1.05em;
}
.plain-cell {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.preview-box {
  min-height: 48px;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
  overflow-x: auto;
}
.import-options {
  display: flex;
  gap: 16px;
  margin: 12px 0;
}
.import-result {
  margin-top: 12px;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
  color: var(--el-text-color-primary);
}
.import-errors {
  margin-top: 8px;
  color: var(--el-color-danger);
  font-size: 12px;
  line-height: 1.7;
}
</style>
