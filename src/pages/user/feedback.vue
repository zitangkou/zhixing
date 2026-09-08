<template>
  <view class="page-feedback" :class="themeClass">
    <nut-textarea
      v-model="content"
      placeholder="请描述题目错误或功能建议..."
      limit-show
      max-length="500"
      rows="6"
    />
    <nut-button type="primary" block class="primary-btn submit-btn" @click="submit">
      提交反馈
    </nut-button>
    <view class="tip">纠错反馈被采纳后可获得 +10 积分</view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Button as NutButton, Textarea as NutTextarea } from '@nutui/nutui-taro'
import { api } from '@/api'
import { useUserStore } from '@/store/user'
import { showToast } from '@/utils/platform'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '反馈建议' })

const { themeClass } = useThemeClass()
const content = ref('')
const userStore = useUserStore()

async function submit() {
  if (!content.value.trim()) {
    showToast('请输入反馈内容')
    return
  }
  const res = await api.submitFeedback(content.value)
  if (res.code === 0) {
    if (res.data.adopted) {
      await userStore.fetchPoints()
      showToast('反馈已采纳，+10积分', 'success')
    } else {
      showToast('感谢您的反馈！', 'success')
    }
    content.value = ''
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
