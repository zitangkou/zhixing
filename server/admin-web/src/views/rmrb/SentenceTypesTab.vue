<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openDialog()">新建类型</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-alert type="info" :closable="false" style="margin-bottom: 12px">
      三刀解剖「第三刀」万能句式的类型下拉选项。
    </el-alert>
    <ListState
      :loading="loading"
      :error="loadError"
      :has-data="rows.length > 0"
      empty-text="暂无句式类型，点击「新建类型」开始"
      @retry="load"
    >
      <template #empty-action>
        <el-button type="primary" @click="openDialog()">新建类型</el-button>
      </template>
      <el-table :data="rows" v-loading="loading && rows.length > 0" row-key="id">
      <el-table-column prop="name" label="类型名" min-width="140" />
      <el-table-column prop="code" label="编码" width="120" />
      <el-table-column prop="tip" label="提示" min-width="200" show-overflow-tooltip />
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

    <el-dialog v-model="visible" :title="editId ? '编辑句式类型' : '新建句式类型'" width="480px">
      <el-form label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="如：辩证论述型" />
        </el-form-item>
        <el-form-item label="编码">
          <el-input v-model="form.code" placeholder="如：dialectic（英文标识）" />
        </el-form-item>
        <el-form-item label="提示">
          <el-input v-model="form.tip" placeholder="如：既要防止…也要避免…" />
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
  createSentenceType,
  deleteSentenceType,
  fetchSentenceTypes,
  updateSentenceType,
  type ShenlunSentenceType,
} from '@/api/rmrb'
import ListState from '@/components/ListState.vue'
import { useAdminList } from '@/composables/useAdminList'

const { loading, loadError, runLoad } = useAdminList()
const saving = ref(false)
const rows = ref<ShenlunSentenceType[]>([])
const visible = ref(false)
const editId = ref<string | null>(null)
const form = reactive({
  name: '',
  code: '',
  tip: '',
  sortOrder: 0,
  isEnabled: true,
})

async function load() {
  await runLoad(async () => {
    rows.value = await fetchSentenceTypes()
  })
}

function openDialog(row?: ShenlunSentenceType) {
  editId.value = row?.id || null
  form.name = row?.name || ''
  form.code = row?.code || ''
  form.tip = row?.tip || ''
  form.sortOrder = row?.sortOrder ?? 0
  form.isEnabled = row?.isEnabled ?? true
  visible.value = true
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写类型名')
    return
  }
  if (!form.code.trim()) {
    ElMessage.warning('请填写编码')
    return
  }
  saving.value = true
  try {
    if (editId.value) {
      await updateSentenceType(editId.value, { ...form })
    } else {
      await createSentenceType({ ...form })
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

async function onToggle(row: ShenlunSentenceType) {
  try {
    await updateSentenceType(row.id, { isEnabled: row.isEnabled })
  } catch (e: any) {
    row.isEnabled = !row.isEnabled
    ElMessage.error(e?.message || '更新失败')
  }
}

async function onDelete(row: ShenlunSentenceType) {
  await ElMessageBox.confirm(`删除类型「${row.name}」？`, '确认')
  await deleteSentenceType(row.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 12px; display: flex; gap: 8px; }
</style>
