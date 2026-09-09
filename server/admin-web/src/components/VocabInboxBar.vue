<template>
  <el-alert v-if="items.length" type="warning" :closable="false" class="inbox-bar">
    <template #title>待收录 {{ items.length }}</template>
    <p class="hint">开采或导入里出现、尚未写入词表的名字。收录后进入正式目录；忽略后不再提示。</p>
    <el-table :data="items" size="small" row-key="id">
      <el-table-column prop="name" label="名称" min-width="140" />
      <el-table-column v-if="showKind" label="种类" width="120">
        <template #default="{ row }">{{ kindLabel(row.kind) }}</template>
      </el-table-column>
      <el-table-column prop="hitCount" label="次数" width="70" />
      <el-table-column prop="sourceTitle" label="最近来源" min-width="160" show-overflow-tooltip />
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button link type="primary" @click="promote(row)">收录</el-button>
          <el-button link @click="ignore(row)">忽略</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-alert>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  fetchRmrbVocabInbox,
  ignoreRmrbVocabInbox,
  promoteRmrbVocabInbox,
  type VocabInboxItem,
} from '@/api/rmrb'
import {
  fetchCategoryVocabInbox,
  ignoreCategoryVocabInbox,
  promoteCategoryVocabInbox,
} from '@/api/categories'

const props = defineProps<{
  kind?: string
  scope?: 'rmrb' | 'category'
}>()

const emit = defineEmits<{ changed: [] }>()

const items = ref<VocabInboxItem[]>([])
const showKind = !props.kind

const LABELS: Record<string, string> = {
  term_category: '规范词分类',
  verb_category: '动词分类',
  sentence_type: '句式类型',
  argument_method: '论证方法',
  skeleton: '骨架模版',
  theory_category: '时政分类',
}

function kindLabel(kind: string) {
  return LABELS[kind] || kind
}

async function load() {
  if (props.scope === 'category') {
    items.value = await fetchCategoryVocabInbox()
    return
  }
  items.value = await fetchRmrbVocabInbox(props.kind)
}

async function promote(row: VocabInboxItem) {
  if (props.scope === 'category') await promoteCategoryVocabInbox(row.id)
  else await promoteRmrbVocabInbox(row.id)
  ElMessage.success(`已收录「${row.name}」`)
  await load()
  emit('changed')
}

async function ignore(row: VocabInboxItem) {
  if (props.scope === 'category') await ignoreCategoryVocabInbox(row.id)
  else await ignoreRmrbVocabInbox(row.id)
  ElMessage.success('已忽略')
  await load()
}

watch(() => props.kind, load)
onMounted(load)
</script>

<style scoped>
.inbox-bar { margin-bottom: 12px; }
.hint { margin: 0 0 8px; font-size: 12px; color: #606266; }
</style>
