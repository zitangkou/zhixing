<template>
  <div class="page">
    <div class="toolbar">
      <el-input v-model="filters.q" placeholder="搜索原文" clearable style="width: 200px" @clear="load" @keyup.enter="load" />
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 130px" @change="load">
        <el-option label="收件箱" value="inbox" />
        <el-option label="已澄清" value="clarified" />
        <el-option label="已内化" value="owned" />
        <el-option label="已运用" value="used" />
      </el-select>
      <el-select v-model="filters.kind" placeholder="类型" clearable style="width: 130px" @change="load">
        <el-option label="金句" value="quote" />
        <el-option label="案例" value="case" />
        <el-option label="观点" value="opinion" />
        <el-option label="数据" value="data" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <span class="stats-tip" v-if="stats">
        共 {{ stats.total }} 条 · 收件箱 {{ stats.inbox }} · 已澄清 {{ stats.clarified }} · 已内化 {{ stats.owned }} · 已运用 {{ stats.used }}
      </span>
    </div>

    <ListState :loading="loading" :error="loadError" :has-data="items.length > 0" empty-text="暂无语料" @retry="load">
      <el-table v-loading="loading && items.length > 0" :data="items" stripe>
        <el-table-column prop="original" label="原文" min-width="260" show-overflow-tooltip />
        <el-table-column prop="kind" label="类型" width="80">
          <template #default="{ row }">
            <el-tag size="small">{{ kindLabel(row.kind) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="标签" min-width="140">
          <template #default="{ row }">
            <el-tag v-for="t in row.tags" :key="t" size="small" class="tag-item">{{ t }}</el-tag>
            <span v-if="!row.tags?.length" class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="sourceTitle" label="来源" width="140" show-overflow-tooltip />
        <el-table-column prop="createdAt" label="创建时间" width="170" :formatter="(row: CorpusItem) => (row.createdAt || '').slice(0, 16).replace('T', ' ')" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link size="small" @click="openEdit(row)">编辑</el-button>
            <el-popconfirm title="确定删除？" @confirm="onDelete(row.id)">
              <template #reference>
                <el-button link size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </ListState>

    <!-- 编辑抽屉 -->
    <el-drawer v-model="drawerVisible" title="编辑语料" size="420px">
      <el-form v-if="editing" label-position="top">
        <el-form-item label="原文">
          <el-input v-model="editing.original" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="白话笔记">
          <el-input v-model="editing.plainNote" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="改写">
          <el-input v-model="editing.rewrite" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="练习">
          <el-input v-model="editing.practice" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editing.status" style="width: 100%">
            <el-option label="收件箱" value="inbox" />
            <el-option label="已澄清" value="clarified" />
            <el-option label="已内化" value="owned" />
            <el-option label="已运用" value="used" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="onSave">保存</el-button>
        </el-form-item>
      </el-form>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { deleteCorpusItem, getCorpusStats, listCorpusItems, updateCorpusItem } from '@/api/corpus'
import type { CorpusItem, CorpusStats } from '@/api/corpus'
import ListState from '@/components/ListState.vue'
import { useAdminList } from '@/composables/useAdminList'

const { loading, loadError, runLoad } = useAdminList()
const items = ref<CorpusItem[]>([])
const stats = ref<CorpusStats | null>(null)
const filters = reactive({ q: '', status: '', kind: '' })
const drawerVisible = ref(false)
const editing = ref<CorpusItem | null>(null)

function kindLabel(k: string) {
  return { quote: '金句', case: '案例', opinion: '观点', data: '数据' }[k] || k
}
function statusLabel(s: string) {
  return { inbox: '收件箱', clarified: '已澄清', owned: '已内化', used: '已运用' }[s] || s
}
function statusType(s: string) {
  return { inbox: 'info', clarified: '', owned: 'warning', used: 'success' }[s] || ''
}

async function load() {
  await runLoad(async () => {
    items.value = await listCorpusItems({
      q: filters.q || undefined,
      status: filters.status || undefined,
      kind: filters.kind || undefined,
    })
    stats.value = await getCorpusStats()
  })
}

function openEdit(row: CorpusItem) {
  editing.value = { ...row }
  drawerVisible.value = true
}

async function onSave() {
  if (!editing.value) return
  await updateCorpusItem(editing.value.id, {
    original: editing.value.original,
    plain_note: editing.value.plainNote,
    rewrite: editing.value.rewrite,
    practice: editing.value.practice,
    status: editing.value.status,
  })
  ElMessage.success('已保存')
  drawerVisible.value = false
  load()
}

async function onDelete(id: string) {
  await deleteCorpusItem(id)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.stats-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.tag-item {
  margin-right: 4px;
}
.muted {
  color: var(--el-text-color-placeholder);
}
</style>
