<template>
  <div class="page">
    <el-card shadow="never" class="block-card">
      <template #header>系统菜单</template>
      <p class="hint">侧栏「系统」里的每一项只认下表中的进入权限。没有该权限时菜单隐藏，直接打开地址也会被拦下。</p>
      <el-table :data="menus" stripe>
        <el-table-column prop="title" label="菜单" width="140" />
        <el-table-column prop="path" label="路由" width="140" />
        <el-table-column prop="permission" label="进入权限" width="160" />
        <el-table-column prop="note" label="说明" min-width="220" />
      </el-table>
    </el-card>

    <el-card shadow="never" class="block-card mt">
      <template #header>操作权限</template>
      <p class="hint">这些权限没有单独菜单，用来控制页面上的修改按钮。</p>
      <el-table :data="actions" stripe>
        <el-table-column prop="code" label="权限码" width="180" />
        <el-table-column prop="label" label="含义" min-width="180" />
        <el-table-column prop="where" label="用在" min-width="200" />
      </el-table>
    </el-card>

    <el-card shadow="never" class="block-card mt">
      <template #header>角色实际授权</template>
      <el-table v-loading="loading" :data="roles" stripe>
        <el-table-column prop="name" label="角色" width="140" />
        <el-table-column prop="code" label="代码" width="140" />
        <el-table-column label="权限">
          <template #default="{ row }">
            <el-tag v-for="code in row.permissions" :key="code" size="small" class="perm-tag">
              {{ labelOf(code) }}
            </el-tag>
            <span v-if="!row.permissions?.length" class="muted">—</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchPermissions, fetchRoles } from '@/api/settings'
import { NAV_GROUPS } from '@/config/nav'

const ACTIONS = [
  { code: 'user:write', where: '用户管理（当前列表只读）' },
  { code: 'feedback:write', where: '反馈建议的采纳 / 驳回' },
  { code: 'xingce:write', where: '行测管理的上传 JSON' },
  { code: 'setting:write', where: '系统设置的保存' },
  { code: 'admin:write', where: '管理员与角色（接口预留）' },
]

const loading = ref(false)
const catalog = ref<Record<string, string>>({})
const roles = ref<Array<{ id: string; code: string; name: string; permissions: string[] }>>([])

const menus = computed(() => {
  const group = NAV_GROUPS.find((item) => item.key === 'system')
  return (group?.children ?? []).map((item) => ({
    title: item.title,
    path: item.path,
    permission: item.permissions.join(' 或 '),
    note: item.permissions.length > 1 ? '任一权限即可进入' : '需要该权限才能看到菜单',
  }))
})

const actions = computed(() =>
  ACTIONS.map((item) => ({
    ...item,
    label: catalog.value[item.code] || item.code,
  })),
)

function labelOf(code: string) {
  const text = catalog.value[code]
  return text ? `${text}（${code}）` : code
}

async function load() {
  loading.value = true
  try {
    const [labels, rows] = await Promise.all([fetchPermissions(), fetchRoles()])
    catalog.value = (labels && typeof labels === 'object' ? labels : {}) as Record<string, string>
    roles.value = rows
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载角色失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.block-card { border: 1px solid var(--admin-border); }
.mt { margin-top: 16px; }
.hint {
  font-size: 13px;
  color: var(--admin-text-muted);
  margin: 0 0 12px;
  line-height: 1.5;
}
.perm-tag { margin: 2px 4px 2px 0; }
.muted { color: var(--admin-text-muted); }
</style>
