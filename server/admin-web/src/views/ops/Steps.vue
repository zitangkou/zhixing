<template>
  <div class="page">
    <el-alert type="info" :closable="false" style="margin-bottom: 12px">
      步骤来自仓内 <code>ops/shenlun</code>、<code>ops/theory</code>。关闭后流程组装里也不会执行。点「执行」会跑命令（多为 --help 探活）；manual / 待确认不跑脚本。
    </el-alert>
    <ListState :loading="loading" :error="loadError" :has-data="rows.length > 0" empty-text="暂无步骤" @retry="load">
      <el-table :data="rows" stripe>
        <el-table-column prop="product" label="产品" width="100" />
        <el-table-column prop="name" label="步骤" min-width="160" />
        <el-table-column prop="stepType" label="类型" width="120" />
        <el-table-column prop="command" label="命令" min-width="220" show-overflow-tooltip />
        <el-table-column label="启用" width="80">
          <template #default="{ row }">
            <el-switch :model-value="row.enabled" @change="(v: boolean) => onToggle(row, v)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="primary" @click="onRun(row)">执行</el-button>
          </template>
        </el-table-column>
      </el-table>
    </ListState>
    <el-dialog v-model="visible" title="编辑步骤" width="560px">
      <el-form label-width="80px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="命令"><el-input v-model="form.command" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="form.notes" type="textarea" :rows="4" /></el-form-item>
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
import { ElMessage } from 'element-plus'
import { fetchOpsSteps, patchOpsStep, runOpsStep, type OpsStep } from '@/api/ops'
import ListState from '@/components/ListState.vue'
import { useAdminList } from '@/composables/useAdminList'

const { loading, loadError, runLoad } = useAdminList()
const rows = ref<OpsStep[]>([])
const visible = ref(false)
const saving = ref(false)
const editId = ref('')
const form = reactive({ name: '', command: '', notes: '' })

async function load() {
  await runLoad(async () => {
    rows.value = await fetchOpsSteps()
  })
}

async function onToggle(row: OpsStep, enabled: boolean) {
  try {
    const updated = await patchOpsStep(row.id, { enabled })
    Object.assign(row, updated)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  }
}

function openEdit(row: OpsStep) {
  editId.value = row.id
  form.name = row.name
  form.command = row.command
  form.notes = row.notes
  visible.value = true
}

async function save() {
  saving.value = true
  try {
    await patchOpsStep(editId.value, { name: form.name, command: form.command, notes: form.notes })
    visible.value = false
    ElMessage.success('已保存')
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function onRun(row: OpsStep) {
  try {
    const res = await runOpsStep(row.id)
    ElMessage[res.ok ? 'success' : 'error'](res.ok ? `${row.name} 完成` : `${row.name} 失败`)
    if (res.output) ElMessage.info(res.output.slice(0, 200))
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '执行失败')
  }
}

onMounted(load)
</script>

<style scoped>
.page { padding-bottom: 24px; }
</style>
