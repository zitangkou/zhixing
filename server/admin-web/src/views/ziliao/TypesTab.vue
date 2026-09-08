<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openDialog()">新建题型</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="rows" v-loading="loading" row-key="id">
      <el-table-column prop="code" label="编码" width="90" />
      <el-table-column prop="name" label="名称" min-width="140" />
      <el-table-column prop="category" label="分类" width="90" />
      <el-table-column prop="difficulty" label="难度" width="70" />
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

    <el-dialog v-model="visible" :title="editId ? '编辑题型' : '新建题型'" width="640px">
      <el-form label-width="90px">
        <el-form-item label="编码"><el-input v-model="form.code" :disabled="!!editId" /></el-form-item>
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="分类"><el-input v-model="form.category" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="考查能力"><el-input v-model="form.ability" /></el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="keywordsText" placeholder="逗号分隔，用于材料组弱匹配" />
        </el-form-item>
        <el-form-item label="难度"><el-input-number v-model="form.difficulty" :min="1" :max="5" /></el-form-item>
        <el-form-item label="频率"><el-input-number v-model="form.examFreq" :min="1" :max="5" /></el-form-item>
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
import { createType, deleteType, listTypes, updateType, type ZiliaoQuestionType } from '@/api/ziliao'

const rows = ref<ZiliaoQuestionType[]>([])
const loading = ref(false)
const visible = ref(false)
const saving = ref(false)
const editId = ref('')
const keywordsText = ref('')
const form = reactive({
  code: '',
  name: '',
  category: '',
  description: '',
  ability: '',
  difficulty: 3,
  examFreq: 3,
  sortOrder: 0,
  isPublished: true,
})

async function load() {
  loading.value = true
  try {
    rows.value = await listTypes()
  } finally {
    loading.value = false
  }
}

function openDialog(row?: ZiliaoQuestionType) {
  editId.value = row?.id || ''
  Object.assign(form, {
    code: row?.code || '',
    name: row?.name || '',
    category: row?.category || '',
    description: row?.description || '',
    ability: row?.ability || '',
    difficulty: row?.difficulty ?? 3,
    examFreq: row?.examFreq ?? 3,
    sortOrder: row?.sortOrder ?? 0,
    isPublished: row?.isPublished ?? true,
  })
  keywordsText.value = (row?.keywords || []).join(',')
  visible.value = true
}

async function save() {
  saving.value = true
  try {
    const keywords = keywordsText.value
      .split(/[,，]/)
      .map((s) => s.trim())
      .filter(Boolean)
    const payload = { ...form, keywords }
    if (editId.value) await updateType(editId.value, payload)
    else await createType(payload)
    visible.value = false
    ElMessage.success('已保存')
    await load()
  } finally {
    saving.value = false
  }
}

async function onToggle(row: ZiliaoQuestionType) {
  await updateType(row.id, { isPublished: row.isPublished })
}

async function onDelete(row: ZiliaoQuestionType) {
  await ElMessageBox.confirm(`删除题型「${row.name}」？`)
  await deleteType(row.id)
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
