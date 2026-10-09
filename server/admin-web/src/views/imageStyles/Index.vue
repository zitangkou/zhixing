<template>
  <div class="page">
    <el-card shadow="never" class="block-card">
      <template #header>
        <div class="card-head">
          <div>
            <div class="title">图片配置</div>
            <div class="subtitle">维护可复用的提示词、风格规则和模型参数；配置按版本化 JSON 保存，便于后续扩展。</div>
          </div>
          <div class="actions">
            <el-button :loading="loading" @click="load">刷新</el-button>
            <el-button v-if="canWrite" @click="openImport">导入 Markdown</el-button>
            <el-button v-if="canWrite" type="primary" @click="openCreate">新增风格</el-button>
          </div>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="当前预置：旅行手账·清透淡彩"
        description="由四张风景测试图多轮归纳。规则控制风格倾向；具体采样强度、参考图权重等 providerParameters 需在选定图像模型后再填写。"
      />

      <el-table v-loading="loading" :data="styles" stripe class="style-table">
        <el-table-column prop="sortOrder" label="排序" width="72" />
        <el-table-column label="风格" min-width="220">
          <template #default="{ row }">
            <div class="style-name">{{ row.name }}</div>
            <div class="muted">{{ row.description }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="slug" label="标识" min-width="180" />
        <el-table-column prop="productKey" label="产品" width="110" />
        <el-table-column prop="version" label="版本" width="100" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">查看 / 编辑</el-button>
            <el-button v-if="canWrite" link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无图片风格配置" />
        </template>
      </el-table>
    </el-card>

    <el-dialog v-model="importVisible" title="从 Markdown 导入图片风格" width="min(780px, 94vw)" destroy-on-close>
      <div class="import-help">
        <div>选择本地整理好的 .md 文件。系统会解析其中的配置并先进行字段校验、重复检查，确认后才会新增风格。</div>
        <a href="/manage/templates/image-style-preset.md" download>下载 Markdown 模板</a>
      </div>
      <el-upload
        :auto-upload="false"
        :show-file-list="false"
        accept=".md,text/markdown,text/plain"
        :on-change="readMarkdownFile"
      >
        <el-button :disabled="!canWrite">选择 Markdown 文件</el-button>
      </el-upload>
      <div v-if="importFileName" class="file-name">已选择：{{ importFileName }}</div>
      <el-alert v-if="importError" class="import-alert" type="error" :closable="false" show-icon :title="importError" />
      <template v-if="importPreview">
        <el-alert
          class="import-alert"
          :type="importPreview.canImport ? 'success' : 'warning'"
          :closable="false"
          show-icon
          :title="importPreview.canImport ? '配置校验通过，可以导入' : importPreview.conflict"
        />
        <el-descriptions :column="2" border class="preview-details">
          <el-descriptions-item label="风格名称">{{ importPreview.style.name }}</el-descriptions-item>
          <el-descriptions-item label="版本">{{ importPreview.style.version }}</el-descriptions-item>
          <el-descriptions-item label="唯一 ID">{{ importPreview.style.id }}</el-descriptions-item>
          <el-descriptions-item label="slug">{{ importPreview.style.slug }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ statusLabel(importPreview.style.status) }}</el-descriptions-item>
          <el-descriptions-item label="产品键">{{ importPreview.style.productKey }}</el-descriptions-item>
          <el-descriptions-item label="简述" :span="2">{{ importPreview.style.description || '—' }}</el-descriptions-item>
        </el-descriptions>
        <el-form label-position="top" class="preview-prompt">
          <el-form-item label="提示词预览"><el-input :model-value="importPreview.style.promptTemplate" type="textarea" :rows="5" readonly /></el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" :disabled="!importPreview?.canImport || !canWrite" @click="confirmImport">确认导入新风格</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑图片风格' : '新增图片风格'" width="min(980px, 94vw)" destroy-on-close>
      <el-form label-position="top" class="style-form">
        <div class="form-grid">
          <el-form-item label="风格名称" required>
            <el-input v-model="form.name" maxlength="64" :disabled="!canWrite" />
          </el-form-item>
          <el-form-item label="唯一 ID" required>
            <el-input v-model="form.id" maxlength="64" placeholder="例如 travel-journal-watercolor" :disabled="editing || !canWrite" />
          </el-form-item>
          <el-form-item label="稳定标识 slug" required>
            <el-input v-model="form.slug" maxlength="80" placeholder="小写英文、数字和连字符" :disabled="!canWrite" />
          </el-form-item>
          <el-form-item label="产品键">
            <el-input v-model="form.productKey" maxlength="32" placeholder="general；* 表示共享" :disabled="!canWrite" />
          </el-form-item>
          <el-form-item label="指定模型">
            <el-select v-model="form.modelId" clearable placeholder="跟随默认模型" :disabled="!canWrite">
              <el-option v-for="model in enabledModels" :key="model.id" :label="`${model.name}${model.credentialConfigured ? '' : '（凭据未就绪）'}`" :value="model.id" :disabled="!model.enabled || !model.credentialConfigured" />
            </el-select>
            <div class="field-hint">留空时使用“工具配置 → 模型配置”中已启用的默认模型。</div>
          </el-form-item>
          <el-form-item label="风格分类">
            <el-input v-model="form.category" maxlength="64" placeholder="image-to-image" :disabled="!canWrite" />
          </el-form-item>
          <el-form-item label="版本">
            <el-input v-model="form.version" maxlength="32" :disabled="!canWrite" />
          </el-form-item>
          <el-form-item label="排序值">
            <el-input-number v-model="form.sortOrder" :min="-10000" :max="10000" :disabled="!canWrite" />
          </el-form-item>
          <el-form-item label="发布状态">
            <el-select v-model="form.status" :disabled="!canWrite">
              <el-option label="草稿（不下发）" value="draft" />
              <el-option label="已启用" value="active" />
              <el-option label="已归档" value="archived" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="简述">
          <el-input v-model="form.description" maxlength="240" :disabled="!canWrite" />
        </el-form-item>
        <el-form-item label="提示词模板" required>
          <el-input v-model="form.promptTemplate" type="textarea" :rows="8" maxlength="12000" show-word-limit :disabled="!canWrite" />
          <div class="field-hint">可使用 <code v-pre>{{scene_description}}</code> 作为场景描述占位符；运行链路接入后由服务端替换。</div>
        </el-form-item>
        <el-form-item label="负面提示词">
          <el-input v-model="form.negativePrompt" type="textarea" :rows="5" maxlength="6000" show-word-limit :disabled="!canWrite" />
        </el-form-item>
        <el-divider content-position="left">可扩展规则与生成参数</el-divider>
        <div class="json-grid">
          <el-form-item label="风格规则 JSON">
            <el-input v-model="rulesJson" type="textarea" :rows="14" spellcheck="false" :disabled="!canWrite" />
          </el-form-item>
          <el-form-item label="语义控制 JSON">
            <el-input v-model="controlsJson" type="textarea" :rows="14" spellcheck="false" :disabled="!canWrite" />
          </el-form-item>
        </div>
        <el-form-item label="模型服务商参数 JSON">
          <el-input v-model="providerParametersJson" type="textarea" :rows="5" spellcheck="false" :disabled="!canWrite" />
          <div class="field-hint">保留为模型适配层参数；当前尚未选定图像模型，因此初始为空对象，不预设未经验证的数值。</div>
        </el-form-item>
        <el-form-item label="维护备注">
          <el-input v-model="form.maintainerNotes" type="textarea" :rows="3" maxlength="2000" :disabled="!canWrite" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
        <el-button v-if="canWrite" type="primary" :loading="saving" @click="save">保存配置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createImageStyle, deleteImageStyle, fetchImageStyles, importImageStyleMarkdown, previewImageStyleMarkdown, updateImageStyle, type ImageStyleImportPreview, type ImageStylePreset } from '@/api/imageStyles'
import { fetchImageModels, type ImageModel } from '@/api/imageModels'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const canWrite = computed(() => auth.hasPermission('setting:write'))
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editing = ref(false)
const styles = ref<ImageStylePreset[]>([])
const imageModels = ref<ImageModel[]>([])
const enabledModels = computed(() => imageModels.value.filter((item) => item.enabled))
const rulesJson = ref('{}')
const controlsJson = ref('{}')
const providerParametersJson = ref('{}')
const importVisible = ref(false)
const importing = ref(false)
const importFileName = ref('')
const importMarkdown = ref('')
const importPreview = ref<ImageStyleImportPreview | null>(null)
const importError = ref('')

function emptyStyle(): ImageStylePreset {
  return {
    id: '', slug: '', name: '', category: 'image-to-image', productKey: 'general', modelId: '', description: '',
    status: 'draft', version: '1.0.0', sortOrder: 100, promptTemplate: '', negativePrompt: '',
    rules: {}, controls: {}, providerParameters: {}, maintainerNotes: '',
  }
}

const form = reactive<ImageStylePreset>(emptyStyle())

function fillForm(style: ImageStylePreset) {
  Object.assign(form, style)
  rulesJson.value = JSON.stringify(style.rules || {}, null, 2)
  controlsJson.value = JSON.stringify(style.controls || {}, null, 2)
  providerParametersJson.value = JSON.stringify(style.providerParameters || {}, null, 2)
}

async function load() {
  loading.value = true
  try {
    const [styleConfig, modelConfig] = await Promise.all([fetchImageStyles(), fetchImageModels()])
    styles.value = styleConfig.items
    imageModels.value = modelConfig.items
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '加载图片风格失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = false
  fillForm(emptyStyle())
  dialogVisible.value = true
}

function openImport() {
  importFileName.value = ''
  importMarkdown.value = ''
  importPreview.value = null
  importError.value = ''
  importVisible.value = true
}

async function readMarkdownFile(uploadFile: { raw?: File; name: string }) {
  importFileName.value = uploadFile.name
  importPreview.value = null
  importError.value = ''
  if (!uploadFile.raw) return
  try {
    if (uploadFile.raw.size > 64 * 1024) throw new Error('文件超过 64 KB，请精简后再导入')
    importMarkdown.value = await uploadFile.raw.text()
    importPreview.value = await previewImageStyleMarkdown(importMarkdown.value)
  } catch (error) {
    importError.value = error instanceof Error ? error.message : '读取或校验 Markdown 失败'
  }
}

async function confirmImport() {
  if (!importMarkdown.value || !importPreview.value?.canImport) return
  importing.value = true
  try {
    const result = await importImageStyleMarkdown(importMarkdown.value)
    ElMessage.success(`已导入“${result.style.name}”`)
    importVisible.value = false
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '导入失败')
  } finally {
    importing.value = false
  }
}

function openEdit(style: ImageStylePreset) {
  editing.value = true
  fillForm(style)
  dialogVisible.value = true
}

function parseJsonObject(text: string, label: string): Record<string, unknown> {
  const parsed: unknown = JSON.parse(text || '{}')
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error(`${label}必须是 JSON 对象`)
  }
  return parsed as Record<string, unknown>
}

async function save() {
  try {
    const payload: ImageStylePreset = {
      ...form,
      id: form.id.trim(),
      slug: form.slug.trim(),
      rules: parseJsonObject(rulesJson.value, '风格规则'),
      controls: parseJsonObject(controlsJson.value, '语义控制'),
      providerParameters: parseJsonObject(providerParametersJson.value, '模型参数'),
    }
    if (!payload.id || !payload.slug || !payload.name.trim()) {
      ElMessage.warning('请填写风格名称、唯一 ID 和 slug')
      return
    }
    saving.value = true
    if (editing.value) await updateImageStyle(payload.id, payload)
    else await createImageStyle(payload)
    ElMessage.success('风格配置已保存')
    dialogVisible.value = false
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(style: ImageStylePreset) {
  try {
    await ElMessageBox.confirm(`删除“${style.name}”配置？`, '删除图片风格', { type: 'warning' })
    await deleteImageStyle(style.id)
    ElMessage.success('已删除')
    await load()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(error instanceof Error ? error.message : '删除失败')
  }
}

function statusLabel(status: ImageStylePreset['status']) {
  return { active: '已启用', draft: '草稿', archived: '已归档' }[status]
}

function statusType(status: ImageStylePreset['status']) {
  return { active: 'success', draft: 'info', archived: 'warning' }[status] as 'success' | 'info' | 'warning'
}

onMounted(load)
</script>

<style scoped>
.block-card { border: 1px solid var(--admin-border); }
.card-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.title { font-size: 16px; font-weight: 650; color: var(--admin-text); }
.subtitle, .muted, .field-hint { color: var(--admin-text-muted); font-size: 12px; line-height: 1.6; }
.subtitle { margin-top: 5px; }
.actions { display: flex; gap: 8px; flex-shrink: 0; }
.style-table { margin-top: 16px; }
.style-name { font-weight: 600; }
.muted { margin-top: 4px; }
.style-form { max-height: min(70vh, 760px); overflow: auto; padding: 0 6px; }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 18px; }
.json-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 18px; }
.field-hint { margin-top: 4px; }
.import-help { display: flex; justify-content: space-between; gap: 16px; margin-bottom: 16px; color: var(--admin-text-muted); font-size: 13px; line-height: 1.6; }
.file-name { margin-top: 10px; color: var(--admin-text-muted); font-size: 12px; }
.import-alert { margin-top: 14px; }
.preview-details { margin-top: 14px; }
.preview-prompt { margin-top: 14px; }
@media (max-width: 720px) { .card-head { align-items: flex-start; flex-direction: column; } .form-grid, .json-grid { grid-template-columns: 1fr; } }
</style>
