<template>
  <div class="library-page">
    <div class="toolbar">
      <div>
        <h2>知库文档</h2>
        <p>通过主应用管理端维护独立知库小程序展示的资料。</p>
      </div>
      <div class="toolbar-actions">
        <el-button :loading="loading" @click="load">刷新</el-button>
        <el-button type="primary" @click="openUpload">上传文档</el-button>
      </div>
    </div>

    <el-alert
      title="文档上传后默认为未发布。确认标题、分类和解析结果后，再发布到知库小程序目录。"
      type="info"
      :closable="false"
      show-icon
      class="library-tip"
    />

    <el-table v-loading="loading" :data="items" stripe empty-text="暂无知库文档">
      <el-table-column prop="title" label="标题" min-width="190" show-overflow-tooltip />
      <el-table-column prop="category" label="分类" width="120" />
      <el-table-column prop="format" label="格式" width="85">
        <template #default="{ row }"><el-tag size="small" effect="plain">{{ row.format.toUpperCase() }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="fileName" label="原文件" min-width="170" show-overflow-tooltip />
      <el-table-column label="解析" width="100">
        <template #default="{ row }">
          <el-tag :type="extractionTag(row.extractionStatus)" size="small">{{ extractionLabel(row.extractionStatus) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }"><el-tag :type="row.isPublished ? 'success' : 'info'" size="small">{{ row.isPublished ? '已发布' : '草稿' }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="createdAt" label="上传时间" width="170">
        <template #default="{ row }">{{ formatDate(row.createdAt) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="205" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="edit(row)">编辑</el-button>
          <el-button link :type="row.isPublished ? 'warning' : 'success'" @click="togglePublish(row)">{{ row.isPublished ? '撤回' : '发布' }}</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="uploadVisible" title="上传知识文档" width="520px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="文件" required>
          <input ref="fileInput" class="file-input" type="file" accept=".md,.txt,.pdf,.docx" @change="onFileChange" />
          <div v-if="selectedFile" class="selected-file">{{ selectedFile.name }} · {{ formatSize(selectedFile.size) }}</div>
          <div class="field-hint">支持 MD、TXT、PDF、DOCX，单文件最大 20 MB</div>
        </el-form-item>
        <el-form-item label="标题" required><el-input v-model="form.title" maxlength="256" show-word-limit /></el-form-item>
        <el-form-item label="分类"><el-input v-model="form.category" maxlength="64" placeholder="例如：AI、商业、设计" /></el-form-item>
        <el-form-item label="简介"><el-input v-model="form.description" type="textarea" :rows="3" maxlength="2000" show-word-limit /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="submitUpload">上传并解析</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editVisible" title="编辑文档信息" width="480px">
      <el-form label-width="72px">
        <el-form-item label="标题"><el-input v-model="form.title" maxlength="256" /></el-form-item>
        <el-form-item label="分类"><el-input v-model="form.category" maxlength="64" /></el-form-item>
        <el-form-item label="简介"><el-input v-model="form.description" type="textarea" :rows="4" maxlength="2000" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="editVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  deleteLibraryDocument,
  fetchLibraryDocuments,
  updateLibraryDocument,
  uploadLibraryDocument,
  type LibraryDocument,
} from '@/api/libraryDocuments'

const items = ref<LibraryDocument[]>([])
const loading = ref(false)
const uploading = ref(false)
const saving = ref(false)
const uploadVisible = ref(false)
const editVisible = ref(false)
const selectedFile = ref<File | null>(null)
const editingId = ref('')
const form = reactive({ title: '', category: '未分类', description: '' })

async function load() {
  loading.value = true
  try { items.value = await fetchLibraryDocuments() }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '文档列表读取失败') }
  finally { loading.value = false }
}
function openUpload() {
  selectedFile.value = null
  Object.assign(form, { title: '', category: '未分类', description: '' })
  uploadVisible.value = true
}
function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] || null
  if (selectedFile.value && !form.title) form.title = selectedFile.value.name.replace(/\.[^.]+$/, '')
}
async function submitUpload() {
  if (!selectedFile.value) { ElMessage.warning('请选择要上传的文件'); return }
  if (!form.title.trim()) { ElMessage.warning('请填写文档标题'); return }
  uploading.value = true
  try {
    await uploadLibraryDocument(selectedFile.value, { title: form.title.trim(), category: form.category.trim() || '未分类', description: form.description.trim() })
    ElMessage.success('上传和解析完成，文档目前为草稿')
    uploadVisible.value = false
    await load()
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '上传失败') }
  finally { uploading.value = false }
}
function edit(row: LibraryDocument) {
  editingId.value = row.id
  Object.assign(form, { title: row.title, category: row.category, description: row.description })
  editVisible.value = true
}
async function saveEdit() {
  if (!form.title.trim()) { ElMessage.warning('标题不能为空'); return }
  saving.value = true
  try {
    await updateLibraryDocument(editingId.value, { title: form.title.trim(), category: form.category.trim() || '未分类', description: form.description.trim() })
    ElMessage.success('文档信息已保存')
    editVisible.value = false
    await load()
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '保存失败') }
  finally { saving.value = false }
}
async function togglePublish(row: LibraryDocument) {
  try {
    await updateLibraryDocument(row.id, { isPublished: !row.isPublished })
    ElMessage.success(row.isPublished ? '文档已撤回' : '文档已发布到知库目录')
    await load()
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '更新发布状态失败') }
}
async function remove(row: LibraryDocument) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.title}」及原文件吗？`, '删除文档', { type: 'warning' })
    await deleteLibraryDocument(row.id)
    ElMessage.success('文档已删除')
    await load()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(error instanceof Error ? error.message : '删除失败')
  }
}
function extractionLabel(status: string) {
  return ({ ready: '已解析', truncated: '已截断', needs_ocr: '待 OCR' } as Record<string, string>)[status] || status
}
function extractionTag(status: string) { return status === 'ready' ? 'success' : status === 'needs_ocr' ? 'warning' : 'info' }
function formatDate(value: string) { return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—' }
function formatSize(bytes: number) { return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB` }

onMounted(load)
</script>

<style scoped>
.library-page { padding: 20px; background: #fff; border-radius: 8px; }
.toolbar { display:flex; align-items:center; justify-content:space-between; margin-bottom:18px; }
.toolbar h2 { margin:0; color:#303133; font-size:20px; }
.toolbar p { margin:7px 0 0; color:#909399; font-size:13px; }
.toolbar-actions { display:flex; gap:8px; }
.library-tip { margin-bottom:18px; }
.file-input { width:100%; font-size:13px; }
.selected-file { margin-top:8px; color:#606266; font-size:12px; }
.field-hint { margin-top:5px; color:#909399; font-size:12px; }
</style>
