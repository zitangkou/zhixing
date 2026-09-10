<template>
  <div class="page">
    <el-alert type="info" :closable="false" style="margin-bottom: 12px">
      多个步骤组成一条流程；流程内可单独关闭某步。cron 只保存，第一期不会定时执行。产物目录见最近一次运行的 materialRoot。自动导入文章/时评为后续能力。
    </el-alert>
    <ListState :loading="loading" :error="loadError" :has-data="rows.length > 0" empty-text="暂无流程" @retry="load">
      <div v-for="p in rows" :key="p.id" class="pipe">
        <div class="pipe-head">
          <strong>{{ p.name }}</strong>
          <el-tag size="small">{{ p.product }}</el-tag>
          <el-switch :model-value="p.enabled" @change="(v: boolean) => onPipeEnabled(p, v)" />
          <span class="cron">cron：{{ p.cron || '未设' }}（不自动跑）</span>
          <el-button size="small" type="primary" @click="onRun(p)">立即执行</el-button>
        </div>
        <p class="notes">{{ p.notes }}</p>
        <el-table :data="p.steps" size="small">
          <el-table-column prop="sortOrder" label="#" width="50" />
          <el-table-column prop="name" label="步骤" min-width="160" />
          <el-table-column prop="stepType" label="类型" width="120" />
          <el-table-column label="本流程启用" width="110">
            <template #default="{ row }">
              <el-switch
                :model-value="row.inPipelineEnabled"
                @change="(v: boolean) => onLinkEnabled(p, row, v)"
              />
            </template>
          </el-table-column>
        </el-table>
      </div>
    </ListState>
    <h3>最近运行</h3>
    <el-table :data="runs" size="small">
      <el-table-column prop="pipelineName" label="流程" min-width="160" />
      <el-table-column prop="status" label="状态" width="140" />
      <el-table-column prop="startedAt" label="开始" width="180" />
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button v-if="row.status === 'waiting_confirm'" link type="primary" @click="onConfirm(row)">
            确认继续
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <pre v-if="lastLog" class="log">{{ lastLog }}</pre>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  confirmOpsRun,
  fetchOpsPipelines,
  fetchOpsRuns,
  patchOpsPipeline,
  runOpsPipeline,
  type OpsPipeline,
  type OpsRun,
  type OpsStep,
} from '@/api/ops'
import ListState from '@/components/ListState.vue'
import { useAdminList } from '@/composables/useAdminList'

const { loading, loadError, runLoad } = useAdminList()
const rows = ref<OpsPipeline[]>([])
const runs = ref<OpsRun[]>([])
const lastLog = ref('')

async function load() {
  await runLoad(async () => {
    rows.value = await fetchOpsPipelines()
    runs.value = await fetchOpsRuns()
  })
}

async function onPipeEnabled(p: OpsPipeline, enabled: boolean) {
  try {
    const updated = await patchOpsPipeline(p.id, { enabled })
    Object.assign(p, updated)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  }
}

async function onLinkEnabled(p: OpsPipeline, step: OpsStep, enabled: boolean) {
  if (!step.linkId) return
  try {
    const updated = await patchOpsPipeline(p.id, { steps: [{ linkId: step.linkId, enabled }] })
    const idx = rows.value.findIndex((x) => x.id === p.id)
    if (idx >= 0) rows.value[idx] = updated
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  }
}

async function onRun(p: OpsPipeline) {
  try {
    const run = await runOpsPipeline(p.id)
    lastLog.value = run.log
    ElMessage.success(`状态：${run.status}`)
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '执行失败')
  }
}

async function onConfirm(row: OpsRun) {
  try {
    const run = await confirmOpsRun(row.id)
    lastLog.value = run.log
    ElMessage.success(`状态：${run.status}`)
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '确认失败')
  }
}

onMounted(load)
</script>

<style scoped>
.pipe { margin-bottom: 28px; padding: 12px; border: 1px solid #ebeef5; border-radius: 8px; }
.pipe-head { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-bottom: 8px; }
.cron { font-size: 12px; color: #909399; }
.notes { font-size: 13px; color: #606266; margin: 0 0 8px; }
.log { font-size: 12px; background: #f5f7fa; padding: 12px; overflow: auto; max-height: 240px; }
</style>
