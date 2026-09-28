<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  fetchKnowledgeVersions,
  rollbackKnowledgeVersion,
  type KnowledgeVersionMeta,
} from '@/api/knowledge'

const props = defineProps<{
  modelValue: boolean
  treeKey: string
}>()

const emit = defineEmits<{
  'update:modelValue': [boolean]
  rolledBack: []
}>()

const loading = ref(false)
const rows = ref<KnowledgeVersionMeta[]>([])

async function load() {
  if (!props.treeKey) return
  loading.value = true
  try {
    rows.value = await fetchKnowledgeVersions(props.treeKey)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载版本失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.modelValue, props.treeKey] as const,
  ([open]) => {
    if (open) void load()
  },
)

async function onRollback(v: number) {
  try {
    await ElMessageBox.confirm(`将 v${v} 的 Markdown 复制为当前草稿（不会自动发布）？`, '回滚到草稿', {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await rollbackKnowledgeVersion(props.treeKey, v)
    ElMessage.success(`已回滚 v${v} 到草稿`)
    emit('rolledBack')
    emit('update:modelValue', false)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '回滚失败')
  }
}
</script>

<template>
  <el-drawer
    :model-value="modelValue"
    title="历史版本"
    size="420px"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-table v-loading="loading" :data="rows" size="small" empty-text="暂无版本">
      <el-table-column prop="version" label="版本" width="70" />
      <el-table-column prop="nodeCount" label="节点" width="70" />
      <el-table-column label="资源" width="80">
        <template #default="{ row }">
          <el-tag :type="row.assetsReady ? 'success' : 'info'" size="small">
            {{ row.assetsReady ? '已上线' : '待图' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="note" label="备注" show-overflow-tooltip />
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="onRollback(row.version)">回滚草稿</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-drawer>
</template>
