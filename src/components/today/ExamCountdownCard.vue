<template>
  <view class="countdown-card" :class="{ editing }">
    <view v-if="loading" class="cd-loading"> 加载考试信息… </view>

    <template v-else-if="!editing">
      <view v-if="countdown" class="cd-main" @tap="startEdit">
        <view class="cd-label"> 距离「{{ countdown.examName }}」还有 </view>
        <view class="cd-number-row">
          <text class="cd-number">
            {{ Math.max(0, countdown.daysLeft) }}
          </text>
          <text class="cd-unit"> 天 </text>
        </view>
        <view class="cd-meta">
          <text>{{ countdown.examDate }}</text>
          <text v-if="countdown.note" class="cd-note">
            {{ countdown.note }}
          </text>
        </view>
        <view class="cd-edit-hint"> 点击修改 › </view>
      </view>
      <view v-else class="cd-empty" @tap="startEdit">
        <text class="cd-empty-title"> 设置目标考试 </text>
        <text class="cd-empty-desc"> 填写考试名称与日期，首页展示倒计时 </text>
      </view>
    </template>

    <view v-else class="cd-editor">
      <text class="cd-editor-title">
        {{ countdown ? '修改考试信息' : '设置目标考试' }}
      </text>
      <nut-input
        v-model="draft.name"
        class="cd-input"
        placeholder="考试名称，如：2027 国考"
        clearable
      />
      <nut-input v-model="draft.date" class="cd-input" type="date" placeholder="考试日期" />
      <nut-input v-model="draft.note" class="cd-input" placeholder="备注（可选）" clearable />
      <view class="cd-actions">
        <nut-button size="small" plain @click="cancelEdit"> 取消 </nut-button>
        <nut-button size="small" type="primary" :loading="saving" @click="save"> 保存 </nut-button>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { Button as NutButton, Input as NutInput } from '@nutui/nutui-taro'
import { api } from '@/api'
import type { ExamCountdown } from '@/types'
import { showConfirm, showToast } from '@/utils/platform'

const countdown = ref<ExamCountdown | null>(null)
const loading = ref(true)
const editing = ref(false)
const saving = ref(false)

const draft = reactive({ name: '', date: '', note: '' })

function todayStr(offsetDays = 0): string {
  const d = new Date()
  d.setDate(d.getDate() + offsetDays)
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${mm}-${dd}`
}

function startEdit() {
  draft.name = countdown.value?.examName || ''
  draft.date = countdown.value?.examDate || todayStr(0)
  draft.note = countdown.value?.note || ''
  editing.value = true
}

function cancelEdit() {
  editing.value = false
}

async function load() {
  loading.value = true
  try {
    const res = await api.getCountdown()
    if (res.code === 0) countdown.value = res.data
  } catch {
    /* 加载失败保持空态 */
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!draft.name.trim()) return showToast('请填写考试名称')
  if (!draft.date) return showToast('请选择考试日期')
  saving.value = true
  try {
    const res = await api.saveCountdown({
      examName: draft.name.trim(),
      examDate: draft.date,
      note: draft.note.trim(),
    })
    if (res.code === 0 && res.data) {
      countdown.value = res.data
      editing.value = false
      showToast('已保存', 'success')
    } else {
      showToast(res.message || '保存失败')
    }
  } catch {
    showToast('网络异常')
  } finally {
    saving.value = false
  }
}

async function remove() {
  if (!countdown.value) return
  const ok = await showConfirm('删除倒计时', '确定删除当前考试倒计时？')
  if (!ok) return
  await api.deleteCountdown()
  countdown.value = null
  showToast('已删除')
}

defineExpose({ load, remove })
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.countdown-card {
  @include card;
  border-radius: $radius-lg;
  background: linear-gradient(135deg, $primary-color 0%, $primary-dark 100%);
  color: $on-primary;
  border: none;
  overflow: hidden;
  &.editing {
    background: $card-bg;
    color: $text-primary;
  }
}

.cd-loading {
  padding: 24px 16px;
  font-size: 13px;
  opacity: 0.85;
  text-align: center;
}

.cd-main {
  padding: 18px 16px 14px;
  text-align: center;
}

.cd-label {
  font-size: 14px;
  opacity: 0.9;
}

.cd-number-row {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 6px;
  margin: 8px 0 4px;
  .cd-number {
    font-size: 52px;
    font-weight: 800;
    line-height: 1;
  }
  .cd-unit {
    font-size: 16px;
    opacity: 0.9;
  }
}

.cd-meta {
  font-size: 12px;
  opacity: 0.85;
  display: flex;
  flex-direction: column;
  gap: 2px;
  .cd-note {
    font-size: 12px;
  }
}

.cd-edit-hint {
  margin-top: 10px;
  font-size: 12px;
  opacity: 0.75;
}

.cd-empty {
  padding: 22px 16px;
  text-align: center;
  .cd-empty-title {
    display: block;
    font-size: 16px;
    font-weight: 700;
  }
  .cd-empty-desc {
    display: block;
    margin-top: 6px;
    font-size: 12px;
    opacity: 0.85;
  }
}

.cd-editor {
  padding: 16px;
  .cd-editor-title {
    display: block;
    font-size: 15px;
    font-weight: 600;
    color: $text-primary;
    margin-bottom: 12px;
  }
  .cd-input {
    margin-bottom: 10px;
  }
  .cd-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 4px;
  }
}
</style>
