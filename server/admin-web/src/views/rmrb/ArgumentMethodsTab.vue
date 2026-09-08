<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openDialog()">新建方法</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-alert type="info" :closable="false" style="margin-bottom: 12px">
      三刀解剖「第二刀」论证骨架里的论证方法下拉：总论点用 overview，分论点用 point。
    </el-alert>
    <ListState
      :loading="loading"
      :error="loadError"
      :has-data="rows.length > 0"
      empty-text="暂无论证方法，点击「新建方法」开始"
      @retry="load"
    >
      <template #empty-action>
        <el-button type="primary" @click="openDialog()">新建方法</el-button>
      </template>
      <el-table :data="rows" v-loading="loading && rows.length > 0" row-key="id">
      <el-table-column prop="name" label="方法名" min-width="180" show-overflow-tooltip />
      <el-table-column label="适用范围" width="110">
        <template #default="{ row }">
          {{ row.scope === 'overview' ? '总论点' : '分论点' }}
        </template>
      </el-table-column>
      <el-table-column prop="note" label="说明" min-width="160" show-overflow-tooltip />
      <el-table-column prop="template" label="步骤模版" min-width="220" show-overflow-tooltip />
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

    <el-dialog v-model="visible" :title="editId ? '编辑论证方法' : '新建论证方法'" width="560px">
      <el-form label-width="90px">
        <el-form-item label="方法名">
          <el-input v-model="form.name" placeholder="如：点例排比 + 类比延伸" />
        </el-form-item>
        <el-form-item label="适用范围">
          <el-radio-group v-model="form.scope">
            <el-radio value="point">分论点</el-radio>
            <el-radio value="overview">总论点</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.note" type="textarea" :rows="2" placeholder="简短用法提示" />
        </el-form-item>
        <el-form-item label="步骤模版">
          <el-input
            v-model="form.template"
            type="textarea"
            :rows="3"
            placeholder="如：提出分论点 → 案例1 → … → 总结升华"
          />
        </el-form-item>
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
  createArgumentMethod,
  deleteArgumentMethod,
  fetchArgumentMethods,
  updateArgumentMethod,
  type ShenlunArgumentMethod,
} from '@/api/rmrb'
import ListState from '@/components/ListState.vue'
import { useAdminList } from '@/composables/useAdminList'

const { loading, loadError, runLoad } = useAdminList()
const saving = ref(false)
const rows = ref<ShenlunArgumentMethod[]>([])
const visible = ref(false)
const editId = ref<string | null>(null)
const form = reactive({
  name: '',
  scope: 'point',
  note: '',
  template: '',
  sortOrder: 0,
  isEnabled: true,
})

async function load() {
  await runLoad(async () => {
    rows.value = await fetchArgumentMethods()
  })
}

function openDialog(row?: ShenlunArgumentMethod) {
  editId.value = row?.id || null
  form.name = row?.name || ''
  form.scope = row?.scope || 'point'
  form.note = row?.note || ''
  form.template = row?.template || ''
  form.sortOrder = row?.sortOrder ?? 0
  form.isEnabled = row?.isEnabled ?? true
  visible.value = true
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写方法名')
    return
  }
  saving.value = true
  try {
    if (editId.value) {
      await updateArgumentMethod(editId.value, { ...form })
    } else {
      await createArgumentMethod({ ...form })
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

async function onToggle(row: ShenlunArgumentMethod) {
  try {
    await updateArgumentMethod(row.id, { isEnabled: row.isEnabled })
  } catch (e: any) {
    row.isEnabled = !row.isEnabled
    ElMessage.error(e?.message || '更新失败')
  }
}

async function onDelete(row: ShenlunArgumentMethod) {
  await ElMessageBox.confirm(`删除方法「${row.name}」？`, '确认')
  await deleteArgumentMethod(row.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 12px; display: flex; gap: 8px; }
</style>
