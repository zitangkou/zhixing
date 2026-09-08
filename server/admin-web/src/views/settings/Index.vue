<template>
  <div class="page">
    <el-card shadow="never" class="block-card">
      <template #header>
        <div class="card-head">
          <span>系统设置</span>
          <el-button :loading="loading" @click="load">刷新</el-button>
        </div>
      </template>
      <p class="hint">
        下方为系统库内配置项。自助注册等开关若未出现在此表，请联系运维在部署配置中修改（不必在此页面操作）。
      </p>
      <el-table v-loading="loading" :data="settings" stripe>
        <el-table-column prop="key" label="键" width="200" />
        <el-table-column prop="description" label="说明" min-width="180" />
        <el-table-column label="值" min-width="220">
          <template #default="{ row }">
            <el-switch
              v-if="isBoolSetting(row)"
              :model-value="row.value === 'true' || row.value === '1'"
              @change="(v: boolean) => onToggle(row, v)"
            />
            <div v-else class="value-row">
              <el-input v-model="row.value" />
              <el-button type="primary" @click="onSave(row)">保存</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never" class="block-card mt">
      <template #header>角色与权限（只读）</template>
      <el-table v-loading="rolesLoading" :data="roles" stripe>
        <el-table-column prop="code" label="代码" width="140" />
        <el-table-column prop="name" label="名称" width="160" />
        <el-table-column label="权限">
          <template #default="{ row }">
            <el-tag v-for="p in row.permissions" :key="p" size="small" class="perm-tag">{{ p }}</el-tag>
            <span v-if="!row.permissions?.length" class="muted">—</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchRoles, fetchSettings, updateSetting, type SettingItem } from '@/api/settings'

const loading = ref(false)
const rolesLoading = ref(false)
const settings = ref<SettingItem[]>([])
const roles = ref<Array<{ id: string; code: string; name: string; permissions: string[] }>>([])

const BOOL_KEYS = new Set(['allow_register', 'llm_enabled'])

function isBoolSetting(row: SettingItem) {
  return BOOL_KEYS.has(row.key) || row.value === 'true' || row.value === 'false'
}

async function load() {
  loading.value = true
  try {
    settings.value = await fetchSettings()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载设置失败')
  } finally {
    loading.value = false
  }
}

async function loadRoles() {
  rolesLoading.value = true
  try {
    roles.value = await fetchRoles()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载角色失败')
  } finally {
    rolesLoading.value = false
  }
}

async function onToggle(row: SettingItem, on: boolean) {
  const value = on ? 'true' : 'false'
  try {
    const updated = await updateSetting(row.key, value)
    row.value = updated.value
    ElMessage.success('已更新')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '更新失败')
    await load()
  }
}

async function onSave(row: SettingItem) {
  try {
    const updated = await updateSetting(row.key, row.value)
    row.value = updated.value
    ElMessage.success('已保存')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  }
}

onMounted(() => {
  load()
  loadRoles()
})
</script>

<style scoped>
.block-card {
  border: 1px solid var(--admin-border);
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.value-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.mt { margin-top: 16px; }
.perm-tag { margin: 2px 4px 2px 0; }
.muted { color: var(--admin-text-muted); }
.hint {
  font-size: 13px;
  color: var(--admin-text-muted);
  margin: 0 0 12px;
  line-height: 1.5;
}
</style>
