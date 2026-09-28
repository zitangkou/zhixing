<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  activateKnowledgeVersion,
  fetchKnowledgeVersions,
  rollbackKnowledgeVersion,
  type KnowledgeVersionMeta,
} from '@/api/knowledge'

const props = defineProps<{
  modelValue: boolean
  treeKey: string
  liveVersion: number
  busy?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [boolean]
  rolledBack: []
  activated: []
  regenerate: [{ version: number; activate: boolean }]
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
  () => [props.modelValue, props.treeKey, props.busy] as const,
  ([open, , busy]) => {
    if (open && !busy) void load()
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

async function onActivate(v: number) {
  try {
    await ElMessageBox.confirm(
      `将 v${v} 设为线上版本？学员端导图与大纲将切换到该版本（节点 id 按路径保留，删除的节点归档）。`,
      '设为线上',
      { type: 'warning' },
    )
  } catch {
    return
  }
  try {
    const r = await activateKnowledgeVersion(props.treeKey, v, props.liveVersion)
    const d = r.nodeDiff
    ElMessage.success(`v${v} 已上线（新增 ${d.added} · 归档 ${d.archived}）`)
    emit('activated')
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '上线失败')
  }
}

function onRegenerate(v: number) {
  emit('regenerate', { version: v, activate: false })
}
</script>

<template>
  <el-drawer
    :model-value="modelValue"
    title="历史版本"
    size="560px"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-table v-loading="loading" :data="rows" size="small" empty-text="暂无版本">
      <el-table-column label="版本" width="80">
        <template #default="{ row }">
          v{{ row.version }}
          <el-tag v-if="row.isLive" type="success" size="small">线上</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="nodeCount" label="节点" width="60" />
      <el-table-column label="图片" width="70">
        <template #default="{ row }">
          <el-tag :type="row.assetsReady ? 'success' : 'info'" size="small">
            {{ row.assetsReady ? '已生成' : '待生成' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="note" label="备注" show-overflow-tooltip />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button
            link
            type="success"
            :disabled="row.isLive || !row.assetsReady || busy"
            @click="onActivate(row.version)"
          >
            设为线上
          </el-button>
          <el-button link type="primary" :disabled="busy" @click="onRegenerate(row.version)">
            {{ row.assetsReady ? '重新生成图片' : '生成图片' }}
          </el-button>
          <el-button link @click="onRollback(row.version)">回滚草稿</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-drawer>
</template>
