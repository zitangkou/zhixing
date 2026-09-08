<template>
  <div>
    <div class="toolbar">
      <el-radio-group v-model="filterKind" size="small" @change="load">
        <el-radio-button value="term">规范词分类</el-radio-button>
        <el-radio-button value="verb">动词分类</el-radio-button>
      </el-radio-group>
      <el-button type="primary" @click="openDialog()">新建分类</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-alert type="info" :closable="false" style="margin-bottom: 12px">
      规范词 / 高频动词分类；移动端三刀页也可快捷新增，修改后立即生效。
    </el-alert>
    <ListState
      :loading="loading"
      :error="loadError"
      :has-data="filteredRows.length > 0"
      :empty-text="`暂无${filterKind === 'verb' ? '动词' : '规范词'}分类，点击「新建分类」开始`"
      @retry="load"
    >
      <template #empty-action>
        <el-button type="primary" @click="openDialog()">新建分类</el-button>
      </template>
      <el-table :data="filteredRows" v-loading="loading && filteredRows.length > 0" row-key="id">
      <el-table-column prop="name" label="分类名" min-width="160" />
      <el-table-column label="类型" width="100">
        <template #default="{ row }">
          {{ row.kind === 'verb' ? '动词' : '规范词' }}
        </template>
      </el-table-column>
      <el-table-column prop="sortOrder" label="排序" width="90" />
      <el-table-column label="启用" width="90">
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

    <el-dialog v-model="visible" :title="editId ? '编辑分类' : '新建分类'" width="420px">
      <el-form label-width="80px">
        <el-form-item label="类型">
          <el-radio-group v-model="form.kind" :disabled="!!editId">
            <el-radio value="term">规范词</el-radio>
            <el-radio value="verb">动词</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="form.name" :placeholder="form.kind === 'verb' ? '如：治理动作' : '如：问题与积弊'" />
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
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createTermCategory,
  deleteTermCategory,
  fetchTermCategories,
  updateTermCategory,
  type ShenlunTermCategory,
} from '@/api/rmrb'
import ListState from '@/components/ListState.vue'
import { useAdminList } from '@/composables/useAdminList'

const { loading, loadError, runLoad } = useAdminList()
const saving = ref(false)
const rows = ref<ShenlunTermCategory[]>([])
const filterKind = ref<'term' | 'verb'>('term')
const visible = ref(false)
const editId = ref<string | null>(null)
const form = reactive({ name: '', kind: 'term' as 'term' | 'verb', sortOrder: 0, isEnabled: true })

const filteredRows = computed(() =>
  rows.value.filter((r) => (r.kind || 'term') === filterKind.value),
)

async function load() {
  await runLoad(async () => {
    rows.value = await fetchTermCategories()
  })
}

function openDialog(row?: ShenlunTermCategory) {
  editId.value = row?.id || null
  form.name = row?.name || ''
  form.kind = (row?.kind as 'term' | 'verb') || filterKind.value
  form.sortOrder = row?.sortOrder ?? 0
  form.isEnabled = row?.isEnabled ?? true
  visible.value = true
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写分类名')
    return
  }
  saving.value = true
  try {
    if (editId.value) {
      await updateTermCategory(editId.value, {
        name: form.name,
        sortOrder: form.sortOrder,
        isEnabled: form.isEnabled,
      })
    } else {
      await createTermCategory({ ...form })
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

async function onToggle(row: ShenlunTermCategory) {
  try {
    await updateTermCategory(row.id, { isEnabled: row.isEnabled })
  } catch (e: any) {
    row.isEnabled = !row.isEnabled
    ElMessage.error(e?.message || '更新失败')
  }
}

async function onDelete(row: ShenlunTermCategory) {
  await ElMessageBox.confirm(`删除分类「${row.name}」？`, '确认')
  await deleteTermCategory(row.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 12px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
</style>
