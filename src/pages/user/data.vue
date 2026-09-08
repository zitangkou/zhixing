<template>
  <view class="page-data" :class="themeClass">
    <view class="section">
      <view class="section-head">
        <text class="section-title">导出数据</text>
        <text class="section-desc">将错题本、语料本、计划复习、积分日志导出为 JSON 文本，可在其他设备导入恢复。</text>
      </view>
      <nut-button type="primary" block class="action-btn" @click="onExport">
        <template #icon>
          <Download color="#fff" size="16" />
        </template>
        导出并复制
      </nut-button>
      <nut-textarea
        v-if="exportText"
        :model-value="exportText"
        placeholder="导出结果将显示在这里..."
        readonly
        rows="6"
        class="result-area"
      />
    </view>

    <view class="section">
      <view class="section-head">
        <text class="section-title">导入数据</text>
        <text class="section-desc">粘贴导出的 JSON 文本，导入将整表替换当前数据（会覆盖本机已有记录）。</text>
      </view>
      <nut-textarea
        v-model="importText"
        placeholder="在此粘贴导出的 JSON 文本..."
        limit-show
        max-length="100000"
        rows="8"
      />
      <nut-button type="primary" block class="action-btn" @click="onImport">
        <template #icon>
          <ArrowUp color="#fff" size="16" />
        </template>
        导入数据
      </nut-button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Taro from '@tarojs/taro'
import { Button as NutButton, Textarea as NutTextarea } from '@nutui/nutui-taro'
import { ArrowUp, Download } from '@nutui/icons-vue-taro'
import { api } from '@/api'
import type { DataExport } from '@/types'
import { showConfirm, showToast } from '@/utils/platform'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '数据导出/导入' })

const { themeClass } = useThemeClass()
const exportText = ref('')
const importText = ref('')

async function onExport() {
  const res = await api.exportCoreData()
  if (res.code !== 0 || !res.data) {
    showToast(res.message || '导出失败')
    return
  }
  const json = JSON.stringify(res.data, null, 2)
  exportText.value = json
  Taro.setClipboardData({ data: json })
  showToast('已导出并复制到剪贴板', 'success')
}

async function onImport() {
  const raw = importText.value.trim()
  if (!raw) {
    showToast('请先粘贴要导入的 JSON 文本')
    return
  }
  let data: DataExport
  try {
    data = JSON.parse(raw) as DataExport
  } catch {
    showToast('JSON 格式不正确，请检查后重试')
    return
  }
  const ok = await showConfirm('确认导入', '导入将覆盖本机现有的错题、语料、计划复习与积分日志，确定继续？')
  if (!ok) return
  const res = await api.importCoreData(data)
  if (res.code !== 0 || !res.data) {
    showToast(res.message || '导入失败')
    return
  }
  const r = res.data
  showToast(
    `导入成功：错题${r.wrongAnswers} · 行测错题${r.manualWrongs} · 语料${r.corpusItems} · 计划${r.planTasks} · 复盘${r.dailyReviews} · 积分${r.pointsLogs}`,
    'success',
  )
  importText.value = ''
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-data {
  @include page-padding;
  .section {
    margin-bottom: 24px;
    .section-head {
      margin-bottom: 12px;
      .section-title {
        display: block;
        font-size: 16px;
        font-weight: 600;
        color: $text-primary;
        margin-bottom: 4px;
      }
      .section-desc {
        display: block;
        font-size: 12px;
        color: $text-muted;
        line-height: 1.5;
      }
    }
    .action-btn {
      margin-bottom: 12px;
    }
    .result-area {
      margin-top: 4px;
    }
  }
}
</style>
