<template>
  <div class="page">
    <div class="toolbar">
      <el-radio-group v-model="dayType" @change="load">
        <el-radio-button v-for="d in days" :key="d.key" :value="d.key">{{ d.label }}</el-radio-button>
      </el-radio-group>
      <el-button type="primary" @click="openDialog()">新增任务</el-button>
      <el-button @click="openCopyDialog">复制到另一天</el-button>
      <el-button :loading="syncing" @click="onSyncPending">同步到未开始清单</el-button>
      <el-button @click="load">刷新</el-button>
    </div>

    <el-alert type="info" :closable="false" style="margin-bottom: 12px">
      每天独立配置。保存/删除模板后，会自动刷新「今天起 14 天内、尚无任何已完成任务」的用户日清单；
      已有完成记录的日期保留不动。也可点「同步到未开始清单」手动再推一次。
      重要级：5=必须完成 / 3=选做 / 2=弹性。
    </el-alert>

    <ListState
      :loading="loading"
      :error="loadError"
      :has-data="templates.length > 0"
      empty-text="当天暂无任务模板，点击「新增任务」开始"
      @retry="load"
    >
      <template #empty-action>
        <el-button type="primary" @click="openDialog()">新增任务</el-button>
      </template>
      <el-table :data="templates" v-loading="loading && templates.length > 0" row-key="id">
      <el-table-column prop="sortOrder" label="序号" width="70" />
      <el-table-column prop="timeSlot" label="时段" width="140" />
      <el-table-column prop="subject" label="科目" width="100" />
      <el-table-column prop="content" label="内容" min-width="240" />
      <el-table-column label="重要级" width="90">
        <template #default="{ row }">
          <el-rate v-model="row.priority" :max="5" disabled />
        </template>
      </el-table-column>
      <el-table-column prop="expectedMinutes" label="预计(min)" width="100" />
      <el-table-column label="启用" width="80">
        <template #default="{ row }">
          <el-switch v-model="row.isActive" @change="onToggleActive(row)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button link type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    </ListState>

    <el-dialog v-model="visible" :title="dialogTitle" width="520px">
      <el-form label-width="90px">
        <el-form-item label="时段">
          <el-input v-model="form.timeSlot" placeholder="如 06:45-07:45" />
        </el-form-item>
        <el-form-item label="科目">
          <el-select v-model="form.subject" allow-create filterable default-first-option>
            <el-option v-for="s in subjects" :key="s" :value="s" :label="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="form.content" type="textarea" :rows="2" placeholder="具体要做什么" />
        </el-form-item>
        <el-form-item label="重要级">
          <el-rate v-model="form.priority" :max="5" :texts="['很低', '低', '中', '高', '最高']" show-text />
        </el-form-item>
        <el-form-item label="预计时长">
          <el-input-number v-model="form.expectedMinutes" :min="0" :max="600" :step="5" />
          <span style="margin-left: 8px; color: #999">分钟</span>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sortOrder" :min="0" />
          <span style="margin-left: 8px; color: #999">数字小的在前</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="copyVisible" title="复制计划到另一天" width="440px">
      <el-form label-width="90px">
        <el-form-item label="从">
          <el-select v-model="copyForm.fromDay" style="width: 100%">
            <el-option v-for="d in days" :key="d.key" :value="d.key" :label="d.label" />
          </el-select>
        </el-form-item>
        <el-form-item label="复制到">
          <el-select v-model="copyForm.toDay" style="width: 100%">
            <el-option
              v-for="d in days"
              :key="d.key"
              :value="d.key"
              :label="d.label"
              :disabled="d.key === copyForm.fromDay"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="方式">
          <el-radio-group v-model="copyForm.replace">
            <el-radio :value="true">覆盖目标日（先清空再写入）</el-radio>
            <el-radio :value="false">追加到目标日</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="copyVisible = false">取消</el-button>
        <el-button type="primary" :loading="copying" @click="onCopy">复制</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  copyPlanDay,
  createPlanTemplate,
  deletePlanTemplate,
  fetchPlanTemplates,
  syncPlanPending,
  updatePlanTemplate,
  type PlanTemplate,
} from '@/api/plan'
import ListState from '@/components/ListState.vue'
import { useAdminList } from '@/composables/useAdminList'

const { loading, loadError, runLoad } = useAdminList()
const saving = ref(false)
const copying = ref(false)
const syncing = ref(false)
const dayType = ref<string>('mon')
const templates = ref<PlanTemplate[]>([])
const visible = ref(false)
const copyVisible = ref(false)
const editId = ref<string | null>(null)
const form = reactive({
  timeSlot: '',
  subject: '',
  content: '',
  priority: 3,
  expectedMinutes: 30,
  sortOrder: 0,
})
const copyForm = reactive({
  fromDay: 'mon',
  toDay: 'tue',
  replace: true,
})

const days = [
  { key: 'mon', label: '周一' },
  { key: 'tue', label: '周二' },
  { key: 'wed', label: '周三' },
  { key: 'thu', label: '周四' },
  { key: 'fri', label: '周五' },
  { key: 'sat', label: '周六' },
  { key: 'sun', label: '周日' },
]

const subjects = ['行测', '申论', '时政', '资料', '阅读', '休息', '复盘', '其他']

const dialogTitle = computed(() => (editId.value ? '编辑任务模板' : '新增任务模板'))

function dayLabel(key: string) {
  return days.find((d) => d.key === key)?.label || key
}

async function load() {
  await runLoad(async () => {
    templates.value = await fetchPlanTemplates(dayType.value)
  })
}

function openDialog(row?: PlanTemplate) {
  if (row) {
    editId.value = row.id
    form.timeSlot = row.timeSlot
    form.subject = row.subject
    form.content = row.content
    form.priority = row.priority
    form.expectedMinutes = row.expectedMinutes
    form.sortOrder = row.sortOrder
  } else {
    editId.value = null
    form.timeSlot = ''
    form.subject = ''
    form.content = ''
    form.priority = 3
    form.expectedMinutes = 30
    form.sortOrder = templates.value.length
  }
  visible.value = true
}

function openCopyDialog() {
  copyForm.fromDay = dayType.value
  copyForm.toDay = dayType.value === 'mon' ? 'tue' : 'mon'
  copyForm.replace = true
  copyVisible.value = true
}

async function onSyncPending() {
  syncing.value = true
  try {
    const r = await syncPlanPending(dayType.value)
    ElMessage.success(
      `已同步「${dayLabel(dayType.value)}」：清理未开始任务 ${r.deletedTasks} 条` +
        (r.skippedDaysWithDone ? `，跳过已有完成 ${r.skippedDaysWithDone} 人日` : ''),
    )
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '同步失败')
  } finally {
    syncing.value = false
  }
}

async function onCopy() {
  if (copyForm.fromDay === copyForm.toDay) {
    ElMessage.warning('源日与目标日不能相同')
    return
  }
  const mode = copyForm.replace ? '覆盖' : '追加到'
  try {
    await ElMessageBox.confirm(
      `将把「${dayLabel(copyForm.fromDay)}」的计划${mode}「${dayLabel(copyForm.toDay)}」，确定？`,
      '复制计划',
      { type: 'warning', confirmButtonText: '确定复制' },
    )
  } catch {
    return
  }
  copying.value = true
  try {
    const r = await copyPlanDay(copyForm.fromDay, copyForm.toDay, copyForm.replace)
    copyVisible.value = false
    if (dayType.value === copyForm.toDay) await load()
    ElMessage.success(
      `已复制：写入 ${r.inserted} 条${r.deleted ? `，清空原目标 ${r.deleted} 条` : ''}（已同步目标日未开始清单）`,
    )
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '复制失败')
  } finally {
    copying.value = false
  }
}

async function save() {
  if (!form.content.trim()) {
    ElMessage.warning('请输入内容')
    return
  }
  saving.value = true
  try {
    if (editId.value) {
      await updatePlanTemplate(editId.value, {
        timeSlot: form.timeSlot,
        subject: form.subject,
        content: form.content.trim(),
        priority: form.priority,
        expectedMinutes: form.expectedMinutes,
        sortOrder: form.sortOrder,
      })
      ElMessage.success('已保存')
    } else {
      await createPlanTemplate({
        dayType: dayType.value as 'weekday' | 'weekend',
        timeSlot: form.timeSlot,
        subject: form.subject,
        content: form.content.trim(),
        priority: form.priority,
        expectedMinutes: form.expectedMinutes,
        sortOrder: form.sortOrder,
      })
      ElMessage.success('已创建')
    }
    visible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function onDelete(row: PlanTemplate) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.content}」？`, '提示', { type: 'warning' })
    await deletePlanTemplate(row.id)
    await load()
    ElMessage.success('已删除')
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e instanceof Error ? e.message : '删除失败')
    }
  }
}

async function onToggleActive(row: PlanTemplate) {
  try {
    await updatePlanTemplate(row.id, { isActive: row.isActive })
    ElMessage.success(row.isActive ? '已启用' : '已停用')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '操作失败')
    row.isActive = !row.isActive
  }
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
  flex-wrap: wrap;
}
</style>
