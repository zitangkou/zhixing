<template>
  <div class="page">
    <div class="toolbar">
      <el-input v-model="filters.q" placeholder="搜索标题" clearable style="width: 200px" @clear="load" @keyup.enter="load" />
      <el-input v-model="filters.userId" placeholder="用户 ID（可选）" clearable style="width: 180px" @clear="load" @keyup.enter="load" />
      <el-button type="primary" @click="load">查询</el-button>
    </div>

    <ListState :loading="loading" :error="loadError" :has-data="items.length > 0" empty-text="暂无事件" @retry="load">
      <el-table v-loading="loading && items.length > 0" :data="items" stripe>
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="eventDate" label="日期" width="120" />
        <el-table-column prop="place" label="地点" width="120" show-overflow-tooltip />
        <el-table-column prop="coreContent" label="核心内容" min-width="260" show-overflow-tooltip />
        <el-table-column prop="knowledgePath" label="知识节点" width="160" show-overflow-tooltip />
        <el-table-column prop="createdAt" label="创建时间" width="170" :formatter="(row: EventItem) => (row.createdAt || '').slice(0, 16).replace('T', ' ')" />
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

    <el-drawer v-model="drawerVisible" title="编辑事件" size="420px">
      <el-form v-if="editing" label-position="top">
        <el-form-item label="标题">
          <el-input v-model="editing.title" />
        </el-form-item>
        <el-form-item label="日期">
          <el-input v-model="editing.eventDate" placeholder="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="地点">
          <el-input v-model="editing.place" />
        </el-form-item>
        <el-form-item label="核心内容">
          <el-input v-model="editing.coreContent" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="笔记">
          <el-input v-model="editing.note" type="textarea" :rows="2" />
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
import { deleteEvent, listEvents, updateEvent } from '@/api/events'
import type { EventItem } from '@/api/events'
import ListState from '@/components/ListState.vue'
import { useAdminList } from '@/composables/useAdminList'

const { loading, loadError, runLoad } = useAdminList()
const items = ref<EventItem[]>([])
const filters = reactive({ q: '', userId: '' })
const drawerVisible = ref(false)
const editing = ref<EventItem | null>(null)

async function load() {
  await runLoad(async () => {
    items.value = await listEvents({
      q: filters.q || undefined,
      userId: filters.userId || undefined,
    })
  })
}

function openEdit(row: EventItem) {
  editing.value = { ...row }
  drawerVisible.value = true
}

async function onSave() {
  if (!editing.value) return
  await updateEvent(editing.value.id, {
    title: editing.value.title,
    event_date: editing.value.eventDate,
    place: editing.value.place,
    core_content: editing.value.coreContent,
    note: editing.value.note,
  })
  ElMessage.success('已保存')
  drawerVisible.value = false
  load()
}

async function onDelete(id: string) {
  await deleteEvent(id)
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
</style>
