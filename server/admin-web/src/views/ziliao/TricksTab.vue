<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openDialog()">新建技巧</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="rows" v-loading="loading" row-key="id">
      <el-table-column prop="code" label="编码" width="90" />
      <el-table-column prop="name" label="名称" min-width="120" />
      <el-table-column prop="category" label="分类" width="90" />
      <el-table-column prop="principle" label="原理" min-width="180" show-overflow-tooltip />
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

    <el-dialog v-model="visible" :title="editId ? '编辑技巧' : '新建技巧'" width="640px">
      <el-form label-width="100px">
        <el-form-item label="编码"><el-input v-model="form.code" :disabled="!!editId" /></el-form-item>
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="分类"><el-input v-model="form.category" /></el-form-item>
        <el-form-item label="原理"><el-input v-model="form.principle" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="何时可用"><el-input v-model="form.whenToUse" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="何时不用"><el-input v-model="form.whenNot" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="误差说明"><el-input v-model="form.errorNote" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="示例"><el-input v-model="form.example" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sortOrder" :min="0" /></el-form-item>
        <el-form-item label="发布"><el-switch v-model="form.isPublished" /></el-form-item>
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
import { createTrick, deleteTrick, listTricks, updateTrick, type ZiliaoTrick } from '@/api/ziliao'

const rows = ref<ZiliaoTrick[]>([])
const loading = ref(false)
const visible = ref(false)
const saving = ref(false)
const editId = ref('')
const form = reactive({
  code: '',
  name: '',
  category: '',
  principle: '',
  whenToUse: '',
  whenNot: '',
  errorNote: '',
  example: '',
  sortOrder: 0,
  isPublished: true,
})

async function load() {
  loading.value = true
  try {
    rows.value = await listTricks()
  } finally {
    loading.value = false
  }
}

function openDialog(row?: ZiliaoTrick) {
  editId.value = row?.id || ''
  Object.assign(form, {
    code: row?.code || '',
    name: row?.name || '',
    category: row?.category || '',
    principle: row?.principle || '',
    whenToUse: row?.whenToUse || '',
    whenNot: row?.whenNot || '',
    errorNote: row?.errorNote || '',
    example: row?.example || '',
    sortOrder: row?.sortOrder ?? 0,
    isPublished: row?.isPublished ?? true,
  })
  visible.value = true
}

async function save() {
  saving.value = true
  try {
    if (editId.value) await updateTrick(editId.value, { ...form })
    else await createTrick({ ...form })
    visible.value = false
    ElMessage.success('已保存')
    await load()
  } finally {
    saving.value = false
  }
}

async function onToggle(row: ZiliaoTrick) {
  await updateTrick(row.id, { isPublished: row.isPublished })
}

async function onDelete(row: ZiliaoTrick) {
  await ElMessageBox.confirm(`删除技巧「${row.name}」？`)
  await deleteTrick(row.id)
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
</style>
