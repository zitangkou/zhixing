<template>
  <view class="page-feedback" :class="themeClass">
    <nut-textarea
      v-model="content"
      placeholder="请描述题目错误或功能建议..."
      limit-show
      max-length="500"
      rows="6"
    />
    <nut-button
      type="primary"
      block
      class="primary-btn submit-btn"
      :loading="submitting"
      :disabled="submitting"
      @click="submit"
    >
      {{ submitting ? '提交中…' : '提交反馈' }}
    </nut-button>
    <view class="tip">纠错反馈被采纳后可获得 +10 积分</view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Taro from '@tarojs/taro'
import { Button as NutButton, Textarea as NutTextarea } from '@nutui/nutui-taro'
import { api } from '@/api'
import { useUserStore } from '@/store/user'
import { showToast } from '@/utils/platform'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '反馈建议' })

const { themeClass } = useThemeClass()
const content = ref('')
const submitting = ref(false)
const userStore = useUserStore()

function leaveAfterSuccess() {
  setTimeout(() => {
    const pages = Taro.getCurrentPages()
    if (pages.length > 1) Taro.navigateBack()
  }, 900)
}

async function submit() {
  const text = content.value.trim()
  if (!text) {
    showToast('请先填写反馈内容', 'none')
    return
  }
  if (submitting.value) return
  submitting.value = true
  try {
    const res = await api.submitFeedback(text)
    if (res.code !== 0) {
      const message = res.message || '提交失败'
      showToast(message, message.length > 7 ? 'none' : 'error')
      return
    }
    content.value = ''
    if (res.data?.adopted) {
      await userStore.fetchPoints()
      showToast('反馈已采纳', 'success')
    } else {
      showToast('提交成功', 'success')
    }
    leaveAfterSuccess()
  } catch (e) {
    const message = e instanceof Error && e.message ? e.message : '提交失败'
    showToast(message, message.length > 7 ? 'none' : 'error')
  } finally {
    submitting.value = false
  }
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-feedback {
  @include page-padding;
  .submit-btn { margin-top: 20px; }
  .tip { text-align: center; margin-top: 12px; font-size: 12px; color: $text-muted; }
}
</style>
