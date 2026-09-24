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
        下方为系统库内配置项。自助注册等开关若未出现在此表，请联系运维在部署配置中修改。
        <template v-if="!canWrite">当前账号只有查看权限，不能修改。</template>
      </p>
      <el-table v-loading="loading" :data="settings" stripe>
        <el-table-column prop="key" label="键" width="200" />
        <el-table-column prop="description" label="说明" min-width="180" />
        <el-table-column label="值" min-width="220">
          <template #default="{ row }">
            <el-switch
              v-if="isBoolSetting(row)"
              :model-value="row.value === 'true' || row.value === '1'"
              :disabled="!canWrite"
              @change="(v: boolean) => onToggle(row, v)"
            />
            <div v-else class="value-row">
              <el-input v-model="row.value" :disabled="!canWrite" />
              <el-button v-if="canWrite" type="primary" @click="onSave(row)">保存</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchSettings, updateSetting, type SettingItem } from '@/api/settings'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const canWrite = computed(() => auth.hasPermission('setting:write'))
const loading = ref(false)
const settings = ref<SettingItem[]>([])

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

onMounted(load)
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
.hint {
  font-size: 13px;
  color: var(--admin-text-muted);
  margin: 0 0 12px;
  line-height: 1.5;
}
</style>
