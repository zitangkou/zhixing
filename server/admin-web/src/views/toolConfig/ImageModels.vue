<template>
  <div class="page">
    <el-card shadow="never" class="model-card">
      <template #header>
        <div class="card-head">
          <div>
            <div class="title">图片模型配置</div>
            <div class="subtitle">维护可选图像模型。风格可单独指定模型；未指定时使用默认模型。</div>
          </div>
          <div class="actions">
            <el-button :loading="loading" @click="load">刷新</el-button>
            <el-button v-if="canWrite" @click="openCreate">新增模型</el-button>
            <el-button v-if="canWrite" type="primary" :loading="saving" @click="save">保存配置</el-button>
          </div>
        </div>
      </template>

      <el-alert
        type="warning"
        :closable="false"
        show-icon
        title="密钥只配置在服务器环境变量中"
        description="本页只填写环境变量名称，不接收或保存密钥值。模型 API 地址必须使用 HTTPS；未配置密钥的模型不能设为可用默认模型。启用模型意味着后端可调用它，实际生成会产生服务商费用。"
      />
      <div class="registry-summary">
        <span>模型数：{{ models.length }}</span>
        <span>已启用：{{ enabledCount }}</span>
        <span>默认模型：{{ defaultName }}</span>
      </div>
      <el-table v-loading="loading" :data="models" stripe>
        <el-table-column label="模型" min-width="190">
          <template #default="{ row }">
            <div class="model-name">{{ row.name }} <el-tag v-if="row.isDefault" size="small" type="success">默认</el-tag></div>
            <div class="muted">{{ providerName(row.provider) }} · {{ row.model }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="baseUrl" label="API 地址" min-width="220" show-overflow-tooltip />
        <el-table-column label="凭据" min-width="150">
          <template #default="{ row }">
            <div>{{ row.credentialEnv || '未填写环境变量名' }}</div>
            <el-tag size="small" :type="row.credentialConfigured ? 'success' : 'warning'">{{ row.credentialConfigured ? '服务器已配置' : '服务器未配置' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }"><el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '已启用' : '已停用' }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row, $index }">
            <el-button link type="primary" @click="openEdit($index)">编辑</el-button>
            <el-button v-if="canWrite" link type="danger" @click="remove($index)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty><el-empty description="尚未配置图片模型" /></template>
      </el-table>
      <el-empty v-if="!models.length && !loading" :image-size="72" description="添加模型后，可在风格配置中选择该模型" />
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingIndex < 0 ? '新增图片模型' : '编辑图片模型'" width="min(720px, 94vw)" destroy-on-close>
      <el-form label-position="top" class="model-form">
        <div class="form-grid">
          <el-form-item label="模型预设" class="preset-field">
            <el-select v-model="selectedPreset" clearable placeholder="选择常用模型，自动填充配置" style="width: 100%" @change="applyPreset">
              <el-option-group v-for="group in presetGroups" :key="group.label" :label="group.label">
                <el-option v-for="preset in group.options" :key="preset.id" :label="preset.label" :value="preset.id" />
              </el-option-group>
            </el-select>
            <div class="field-hint">预设只填充公开模型参数，不包含密钥；具体价格以服务商控制台为准。</div>
          </el-form-item>
          <el-form-item label="唯一 ID" required><el-input v-model="form.id" :disabled="editingIndex >= 0" placeholder="例如 wan26-image" /></el-form-item>
          <el-form-item label="后台名称" required><el-input v-model="form.name" placeholder="例如 万相 2.6 图片编辑" /></el-form-item>
          <el-form-item label="服务商适配器" required>
            <el-select v-model="form.provider" style="width: 100%">
              <el-option label="阿里云百炼 DashScope" value="dashscope" />
              <el-option label="火山引擎 Ark" value="volcengine" />
              <el-option label="OpenAI 兼容图像编辑接口" value="openai-compatible" />
            </el-select>
          </el-form-item>
          <el-form-item label="服务商模型 ID" required><el-input v-model="form.model" placeholder="例如 wan2.6-image 或 Ark Endpoint ID" /></el-form-item>
          <el-form-item label="API Base URL（HTTPS）" required><el-input v-model="form.baseUrl" placeholder="https://.../api/v1" /></el-form-item>
          <el-form-item label="密钥环境变量名"><el-input :model-value="credentialEnvName" disabled /></el-form-item>
          <el-form-item label="请求超时（秒）"><el-input-number v-model="form.timeoutSeconds" :min="10" :max="600" /></el-form-item>
          <el-form-item label="能力"><el-checkbox v-model="form.supportsImageEdit">支持图片编辑 / 图生图</el-checkbox></el-form-item>
        </div>
        <el-form-item label="模型专属参数 JSON"><el-input v-model="parametersJson" type="textarea" :rows="5" spellcheck="false" /></el-form-item>
        <div class="switch-row">
          <el-checkbox v-model="form.enabled">启用模型</el-checkbox>
          <el-checkbox v-model="form.isDefault" :disabled="!form.enabled">设为默认模型</el-checkbox>
        </div>
        <p class="form-note">保存仅更新模型目录。服务器需另外设置对应环境变量值并重启后端；未配好凭据时，模型会显示为未就绪。</p>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!canWrite" @click="applyForm">应用到列表</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchImageModels, saveImageModels, type ImageModel } from '@/api/imageModels'
import { useAuthStore } from '@/stores/auth'

const presetGroups = [
  {
    label: '阿里云百炼',
    options: [
      { id: 'wan26-image', label: '万相 2.6 图像编辑 · 约 ¥0.20/张' },
    ],
  },
  {
    label: '火山引擎 Ark · 豆包 Seedream',
    options: [
      { id: 'seedream-40', label: 'Seedream 4.0 · 约 ¥0.20/张' },
      { id: 'seedream-45', label: 'Seedream 4.5 · 约 ¥0.25/张' },
    ],
  },
]
const presets: Record<string, Partial<ImageModel>> = {
  'wan26-image': { id: 'wan26-image', name: '万相 2.6 图像编辑', provider: 'dashscope', model: 'wan2.6-image', baseUrl: 'https://dashscope.aliyuncs.com/api/v1', credentialEnv: 'DASHSCOPE_API_KEY', parameters: { enable_interleave: false, size: '1K', n: 1 } },
  'seedream-40': { id: 'seedream-40', name: '豆包 Seedream 4.0', provider: 'volcengine', model: 'doubao-seedream-4-0-250828', baseUrl: 'https://ark.cn-beijing.volces.com/api/v3', credentialEnv: 'ARK_API_KEY', parameters: { response_format: 'url', size: '2K', sequential_image_generation: 'disabled' } },
  'seedream-45': { id: 'seedream-45', name: '豆包 Seedream 4.5', provider: 'volcengine', model: 'doubao-seedream-4-5-251128', baseUrl: 'https://ark.cn-beijing.volces.com/api/v3', credentialEnv: 'ARK_API_KEY', parameters: { response_format: 'url', size: '2K', sequential_image_generation: 'disabled' } },
}
function providerName(provider: ImageModel['provider']) {
  return ({ dashscope: '阿里云百炼', volcengine: '火山引擎 Ark', 'openai-compatible': 'OpenAI 兼容接口' })[provider]
}

const auth = useAuthStore()
const canWrite = computed(() => auth.hasPermission('setting:write'))
const models = ref<ImageModel[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingIndex = ref(-1)
const parametersJson = ref('{}')
const selectedPreset = ref('')
const enabledCount = computed(() => models.value.filter((item) => item.enabled).length)
const defaultName = computed(() => models.value.find((item) => item.isDefault)?.name || '未设置')
const credentialEnvName = computed(() => ({ dashscope: 'DASHSCOPE_API_KEY', volcengine: 'ARK_API_KEY', 'openai-compatible': 'OPENAI_IMAGE_API_KEY' })[form.provider])

function blankModel(): ImageModel {
  return { id: '', name: '', provider: 'dashscope', model: '', baseUrl: 'https://dashscope.aliyuncs.com/api/v1', credentialEnv: 'DASHSCOPE_API_KEY', enabled: false, isDefault: false, supportsImageEdit: true, timeoutSeconds: 180, parameters: {} }
}
const form = reactive<ImageModel>(blankModel())

async function load() {
  loading.value = true
  try { models.value = (await fetchImageModels()).items }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '加载模型配置失败') }
  finally { loading.value = false }
}

function openCreate() {
  editingIndex.value = -1
  Object.assign(form, blankModel())
  parametersJson.value = '{}'
  selectedPreset.value = ''
  dialogVisible.value = true
}

function openEdit(index: number) {
  editingIndex.value = index
  Object.assign(form, JSON.parse(JSON.stringify(models.value[index])))
  parametersJson.value = JSON.stringify(form.parameters || {}, null, 2)
  selectedPreset.value = ''
  dialogVisible.value = true
}

function applyPreset(presetId: string) {
  const preset = presets[presetId]
  if (!preset) return
  const keep = editingIndex.value >= 0
    ? { id: form.id, enabled: form.enabled, isDefault: form.isDefault }
    : {}
  Object.assign(form, blankModel(), preset, keep)
  parametersJson.value = JSON.stringify(preset.parameters || {}, null, 2)
}

function applyForm() {
  try {
    const parameters: unknown = JSON.parse(parametersJson.value || '{}')
    if (!parameters || typeof parameters !== 'object' || Array.isArray(parameters)) throw new Error('模型参数必须为 JSON 对象')
    if (!form.id.trim() || !form.name.trim() || !form.model.trim() || !form.baseUrl.trim()) throw new Error('请填写模型 ID、名称、服务商模型 ID 和 API 地址')
    const next = { ...JSON.parse(JSON.stringify(form)), id: form.id.trim(), name: form.name.trim(), model: form.model.trim(), baseUrl: form.baseUrl.trim(), credentialEnv: credentialEnvName.value, parameters } as ImageModel
    if (next.isDefault && !next.enabled) throw new Error('默认模型必须启用')
    if (models.value.some((item, index) => item.id === next.id && index !== editingIndex.value)) throw new Error('模型 ID 已存在')
    const updated = [...models.value]
    if (next.isDefault) updated.forEach((item) => { item.isDefault = false })
    if (editingIndex.value < 0) updated.push(next)
    else updated[editingIndex.value] = next
    models.value = updated
    dialogVisible.value = false
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '模型参数格式错误') }
}

async function remove(index: number) {
  try {
    await ElMessageBox.confirm(`删除模型“${models.value[index].name}”？引用该模型的风格需要改为默认模型或其他模型。`, '删除图片模型', { type: 'warning' })
    models.value.splice(index, 1)
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error('删除失败') }
}

async function save() {
  saving.value = true
  try {
    models.value = (await saveImageModels(models.value)).items
    ElMessage.success('模型配置已保存')
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '保存模型配置失败') }
  finally { saving.value = false }
}

onMounted(load)
</script>

<style scoped>
.model-card { border: 1px solid var(--admin-border); }
.card-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.title { color: var(--admin-text); font-size: 16px; font-weight: 650; }
.subtitle, .muted, .form-note { color: var(--admin-text-muted); font-size: 12px; line-height: 1.6; }
.subtitle { margin-top: 5px; }
.actions { display: flex; gap: 8px; flex-shrink: 0; }
.registry-summary { display: flex; gap: 22px; margin: 18px 0 12px; color: var(--admin-text-muted); font-size: 12px; }
.model-name { color: var(--admin-text); font-weight: 600; }
.muted { margin-top: 4px; }
.model-form { max-height: min(70vh, 720px); overflow: auto; padding: 0 6px; }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 16px; }
.preset-field { grid-column: 1 / -1; }
.field-hint { margin-top: 5px; color: var(--admin-text-muted); font-size: 12px; line-height: 1.5; }
.switch-row { display: flex; gap: 24px; margin-bottom: 14px; }
.form-note { margin: 0; }
@media (max-width: 720px) { .card-head { align-items: flex-start; flex-direction: column; } .form-grid { grid-template-columns: 1fr; } .registry-summary { flex-wrap: wrap; gap: 10px 16px; } }
</style>
