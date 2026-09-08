<template>
  <div class="page">
    <ListState
      :loading="loading"
      :error="loadError"
      :has-data="users.length > 0"
      empty-text="暂无用户"
      @retry="load"
    >
      <el-table v-loading="loading && users.length > 0" :data="users" stripe>
        <el-table-column prop="id" label="ID" width="140" />
        <el-table-column prop="nickname" label="昵称" width="140" />
        <el-table-column prop="points" label="积分" width="100" />
        <el-table-column label="会员" width="80">
          <template #default="{ row }">{{ row.is_member ? '是' : '否' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" min-width="180" />
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        class="pager"
        @current-change="load"
        @size-change="onPageSizeChange"
      />
    </ListState>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchUsers } from '@/api/users'
import ListState from '@/components/ListState.vue'
import { useAdminList } from '@/composables/useAdminList'
import type { AppUser } from '@/types'

const { loading, loadError, runLoad } = useAdminList()
const users = ref<AppUser[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

async function load() {
  await runLoad(async () => {
    const data = await fetchUsers({ page: page.value, page_size: pageSize.value })
    users.value = data.items
    total.value = data.total
  })
}

function onPageSizeChange() {
  page.value = 1
  load()
}

onMounted(load)
</script>

<style scoped>
.pager { margin-top: 16px; justify-content: flex-end; }
</style>
