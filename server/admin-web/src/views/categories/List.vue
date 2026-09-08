<template>
  <div class="page">
    <div class="toolbar">
      <el-button type="primary" @click="openDialog()">新增分类</el-button>
      <el-button @click="load">刷新</el-button>
    </div>

    <ListState
      :loading="loading"
      :error="loadError"
      :has-data="flatCategories.length > 0"
      empty-text="暂无分类，点击「新增分类」开始"
      @retry="load"
    >
      <template #empty-action>
        <el-button type="primary" @click="openDialog()">新增分类</el-button>
      </template>
      <el-table :data="flatCategories" v-loading="loading && flatCategories.length > 0" row-key="id" default-expand-all>
      <el-table-column prop="name" label="分类名称" min-width="200" />
      <el-table-column prop="level" label="层级" width="80" />
      <el-table-column prop="sortOrder" label="排序" width="80" />
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row, true)">添加子类</el-button>
          <el-button link type="danger" @click="onDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    </ListState>

    <el-dialog v-model="visible" :title="dialogTitle" width="420px">
      <el-form label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" />
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
import { createCategory, deleteCategory, fetchCategories } from '@/api/categories'
import ListState from '@/components/ListState.vue'
import { useAdminList } from '@/composables/useAdminList'
import type { Category } from '@/types'

interface FlatCategory {
  id: string
  name: string
  level: number
  sortOrder: number
  children?: FlatCategory[]
}

const { loading, loadError, runLoad } = useAdminList()
const saving = ref(false)
const tree = ref<Category[]>([])
const visible = ref(false)
const parentId = ref<string | null>(null)
const form = reactive({ name: '', sort_order: 0 })

const flatCategories = computed(() => flatten(tree.value))

function flatten(list: Category[], level = 1): FlatCategory[] {
  return list.map((item) => ({
    id: item.id,
    name: item.name,
    level,
    sortOrder: item.sortOrder || 0,
    children: item.children?.length ? flatten(item.children, level + 1) : undefined,
  }))
}

const dialogTitle = computed(() => (parentId.value ? '添加子分类' : '新增分类'))

async function load() {
  await runLoad(async () => {
    tree.value = await fetchCategories()
  })
}

function openDialog(parent?: FlatCategory, asChild = false) {
  parentId.value = asChild && parent ? parent.id : null
  form.name = ''
  form.sort_order = 0
  visible.value = true
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入分类名称')
    return
  }
  saving.value = true
  try {
    await createCategory({
      name: form.name.trim(),
      parent_id: parentId.value,
      sort_order: form.sort_order,
    })
    visible.value = false
    await load()
    ElMessage.success('已创建')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '创建失败')
  } finally {
    saving.value = false
  }
}

async function onDelete(id: string) {
  await ElMessageBox.confirm('确定删除该分类？', '提示', { type: 'warning' })
  try {
    await deleteCategory(id)
    await load()
    ElMessage.success('已删除')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '删除失败')
  }
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
</style>
