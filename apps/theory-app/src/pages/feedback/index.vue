<template>
  <view class="page-feedback">
    <view class="eyebrow">意见反馈</view>
    <view class="page-title">纠错与建议</view>
    <view class="card">
      <textarea
        v-model="content"
        class="feedback-input"
        placeholder-class="feedback-placeholder"
        placeholder="例如：某道题的答案或解析有误；或你希望增加的功能"
        :maxlength="500"
      />
      <view class="feedback-count">{{ content.length }}/500</view>
    </view>
    <button class="feedback-submit" :disabled="loading || !content.trim()" @tap="submit">
      {{ loading ? '提交中…' : '提交反馈' }}
    </button>
    <view class="feedback-tip">反馈会被真实记录并逐条查看，采纳后会发放积分奖励。</view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/api'
import { showToast } from '@/utils/platform'

const content = ref('')
const loading = ref(false)

async function submit() {
  const text = content.value.trim()
  if (!text) return showToast('请输入反馈内容')
  loading.value = true
  const response = await api.submitFeedback(text)
  loading.value = false
  if (response.code === 0) {
    content.value = ''
    showToast('已收到你的反馈，感谢！', 'success')
  } else {
    showToast(response.message || '提交失败，请稍后再试')
  }
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-feedback {
  @include page-padding;
}

.feedback-input {
  width: 100%;
  min-height: 132px;
  box-sizing: border-box;
  padding: 12px;
  border: 1px solid $border-color;
  border-radius: 12px;
  background: $page-bg;
  color: $text-primary;
  font-size: 14px;
  line-height: 1.7;
}

.feedback-placeholder {
  color: $text-muted;
  font-size: 13px;
}

.feedback-count {
  margin-top: 6px;
  text-align: right;
  color: $text-muted;
  font-size: 11px;
}

.feedback-submit {
  width: 100%;
  height: 48px;
  box-sizing: border-box;
  margin-top: 18px;
  border: 0;
  border-radius: 24px;
  background: linear-gradient(135deg, $primary-color, $primary-dark);
  color: $on-primary;
  font-size: 15px;
  font-weight: 700;
  line-height: 48px;
}

.feedback-submit::after {
  border: 0;
}

.feedback-submit[disabled] {
  opacity: 0.55;
}

.feedback-tip {
  margin-top: 14px;
  text-align: center;
  color: $text-muted;
  font-size: 12px;
  line-height: 1.7;
}
</style>
