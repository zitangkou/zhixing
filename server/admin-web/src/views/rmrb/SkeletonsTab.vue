<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openDialog()">新建模版</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-alert type="info" :closable="false" style="margin-bottom: 12px">
      三刀解剖「第二刀」先选模版再填写。线性模版适合问题-原因-对策；分论点模版适合总分结构。
    </el-alert>
    <ListState
      :loading="loading"
      :error="loadError"
      :has-data="rows.length > 0"
      empty-text="暂无骨架模版，点击「新建模版」开始"
      @retry="load"
    >
      <template #empty-action>
        <el-button type="primary" @click="openDialog()">新建模版</el-button>
      </template>
      <el-table :data="rows" v-loading="loading && rows.length > 0" row-key="id">
      <el-table-column prop="name" label="模版名" min-width="140" />
      <el-table-column prop="mode" label="类型" width="100">
        <template #default="{ row }">{{ row.mode === 'points' ? '分论点' : '线性步骤' }}</template>
      </el-table-column>
      <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip />
      <el-table-column prop="sortOrder" label="排序" width="80" />
      <el-table-column label="启用" width="80">
        <template #default="{ row }">
          <el-switch v-model="row.isEnabled" @change="onToggle(row)" />
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

    <el-dialog v-model="visible" :title="editId ? '编辑骨架模版' : '新建骨架模版'" width="640px">
      <el-form label-width="100px">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="如：问题-原因-对策" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" />
        </el-form-item>
        <el-form-item label="结构类型">
          <el-radio-group v-model="form.mode">
            <el-radio value="linear">线性步骤</el-radio>
            <el-radio value="points">总分分论点</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.mode === 'linear'" label="步骤标签">
          <el-input
            v-model="linearLabels"
            placeholder="用逗号分隔，如：问题,原因,对策"
          />
          <div class="hint">保存时按标签生成填写槽位</div>
        </el-form-item>
        <template v-else>
          <el-form-item label="总论点标签">
            <el-input v-model="form.structure.overviewLabel" placeholder="总论点" />
          </el-form-item>
          <el-form-item label="总论点提示">
            <el-input v-model="form.structure.overviewPlaceholder" placeholder="一句话总论点" />
          </el-form-item>
          <el-alert type="info" :closable="false" style="margin-bottom: 12px">
            总分结构：总论点 → 分论点（标题 + 可选论据/小结 + 论证方法/模板）→ 总结。
          </el-alert>
        </template>
        <el-form-item label="排序">
          <el-input-number v-model="form.sortOrder" :min="0" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.isEnabled" />
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
  createSkeletonTemplate,
  deleteSkeletonTemplate,
  fetchSkeletonTemplates,
  updateSkeletonTemplate,
  type ShenlunSkeletonFieldDef,
  type ShenlunSkeletonTemplate,
} from '@/api/rmrb'
import ListState from '@/components/ListState.vue'
import { useAdminList } from '@/composables/useAdminList'

const { loading, loadError, runLoad } = useAdminList()
const saving = ref(false)
const rows = ref<ShenlunSkeletonTemplate[]>([])
const visible = ref(false)
const editId = ref<string | null>(null)
const linearLabels = ref('问题,原因,对策')

const defaultPointFields: ShenlunSkeletonFieldDef[] = [
  { key: 'title', label: '标题', placeholder: '分论点标题' },
  { key: 'evidence', label: '论据', placeholder: '可选：事实/案例/论述' },
  { key: 'summary', label: '小结', placeholder: '可选：本点收束' },
]

const form = reactive({
  name: '',
  description: '',
  mode: 'linear' as 'linear' | 'points',
  sortOrder: 0,
  isEnabled: true,
  structure: {
    mode: 'linear' as string,
    fields: [] as ShenlunSkeletonFieldDef[],
    overviewLabel: '总论点',
    overviewPlaceholder: '一句话总论点',
    pointFields: [...defaultPointFields] as ShenlunSkeletonFieldDef[],
  },
})

function normalizeFields(list?: ShenlunSkeletonFieldDef[]): ShenlunSkeletonFieldDef[] {
  return (list || []).map((f) => ({
    key: f.key,
    label: f.label,
    placeholder: f.placeholder || '',
  }))
}

function buildLinearFields(labels: string): ShenlunSkeletonFieldDef[] {
  return labels
    .split(/[,，、]/)
    .map((s) => s.trim())
    .filter(Boolean)
    .map((label, i) => ({
      key: `step_${i + 1}`,
      label,
      placeholder: '',
    }))
}

async function load() {
  await runLoad(async () => {
    rows.value = await fetchSkeletonTemplates()
  })
}

function openDialog(row?: ShenlunSkeletonTemplate) {
  editId.value = row?.id || null
  form.name = row?.name || ''
  form.description = row?.description || ''
  form.mode = (row?.mode === 'points' ? 'points' : 'linear')
  form.sortOrder = row?.sortOrder ?? 0
  form.isEnabled = row?.isEnabled ?? true
  if (row?.structure) {
    form.structure.mode = row.structure.mode
    form.structure.fields = normalizeFields(row.structure.fields)
    form.structure.overviewLabel = row.structure.overviewLabel || '全文总骨架'
    form.structure.overviewPlaceholder = row.structure.overviewPlaceholder || ''
    form.structure.pointFields = row.structure.pointFields?.length
      ? normalizeFields(row.structure.pointFields)
      : [...defaultPointFields]
    linearLabels.value = (row.structure.fields || []).map((f) => f.label).join(',') || '问题,原因,对策'
  } else {
    form.structure.fields = []
    form.structure.pointFields = [...defaultPointFields]
    linearLabels.value = '问题,原因,对策'
  }
  visible.value = true
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写模版名')
    return
  }
  const structure =
    form.mode === 'linear'
      ? {
          mode: 'linear',
          fields: buildLinearFields(linearLabels.value),
          overviewLabel: '',
          overviewPlaceholder: '',
          pointFields: [],
        }
      : {
          mode: 'points',
          fields: [],
          overviewLabel: form.structure.overviewLabel,
          overviewPlaceholder: form.structure.overviewPlaceholder,
          pointFields: form.structure.pointFields,
        }
  if (form.mode === 'linear' && !structure.fields.length) {
    ElMessage.warning('请填写至少一个步骤标签')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      description: form.description.trim(),
      mode: form.mode,
      structure,
      sortOrder: form.sortOrder,
      isEnabled: form.isEnabled,
    }
    if (editId.value) {
      await updateSkeletonTemplate(editId.value, payload)
    } else {
      await createSkeletonTemplate(payload)
    }
    ElMessage.success('已保存')
    visible.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function onToggle(row: ShenlunSkeletonTemplate) {
  try {
    await updateSkeletonTemplate(row.id, { isEnabled: row.isEnabled })
  } catch (e: any) {
    row.isEnabled = !row.isEnabled
    ElMessage.error(e?.message || '更新失败')
  }
}

async function onDelete(row: ShenlunSkeletonTemplate) {
  await ElMessageBox.confirm(`删除模版「${row.name}」？`, '确认')
  await deleteSkeletonTemplate(row.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 12px; display: flex; gap: 8px; }
.hint { font-size: 12px; color: #909399; margin-top: 4px; }
</style>
