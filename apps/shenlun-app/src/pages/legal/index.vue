<template>
  <view class="legal-page">
    <view class="legal-tabs">
      <view class="legal-tab" :class="{ 'legal-tab-active': doc === 'agreement' }" @tap="pick('agreement')">用户协议</view>
      <view class="legal-tab" :class="{ 'legal-tab-active': doc === 'privacy' }" @tap="pick('privacy')">隐私政策</view>
    </view>

    <view class="legal-meta">{{ APP_NAME }} · 生效日期 {{ LEGAL_EFFECTIVE_DATE }}</view>

    <view v-for="section in sections" :key="section.h" class="legal-card">
      <view class="legal-h">{{ section.h }}</view>
      <view v-for="(line, i) in section.p || []" :key="`p-${i}`" class="legal-p">{{ line }}</view>
      <view v-for="(line, i) in section.list || []" :key="`l-${i}`" class="legal-li">
        <text class="legal-dot">·</text>
        <text class="legal-li-text">{{ line }}</text>
      </view>
    </view>

    <view class="legal-end">— 正文完 —</view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import Taro, { useRouter } from '@tarojs/taro'
import { APP_NAME, LEGAL_EFFECTIVE_DATE, PRIVACY_POLICY, USER_AGREEMENT } from '@/constants/legal'

const router = useRouter()
const doc = ref<'agreement' | 'privacy'>(router.params?.doc === 'privacy' ? 'privacy' : 'agreement')
const sections = computed(() => (doc.value === 'privacy' ? PRIVACY_POLICY : USER_AGREEMENT))

function pick(next: 'agreement' | 'privacy') {
  if (doc.value === next) return
  doc.value = next
  Taro.pageScrollTo({ scrollTop: 0, duration: 0 })
}
</script>

<style scoped lang="scss">
@import '@/styles/variables.scss';

.legal-page {
  @include page-padding;
}

.legal-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.legal-tab {
  flex: 1;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: $radius-md;
  background: $card-bg;
  color: $text-secondary;
  font-size: 14px;
  border: 1px solid $border-color;
}

.legal-tab-active {
  background: $primary-light;
  border-color: $primary-color;
  color: $primary-color;
  font-weight: 600;
}

.legal-meta {
  font-size: 12px;
  color: $text-muted;
  padding: 0 2px 10px;
}

.legal-card {
  @include card;
}

.legal-h {
  font-size: 15px;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 10px;
}

.legal-p {
  font-size: 13px;
  line-height: 22px;
  color: $text-secondary;
  margin-bottom: 8px;
}

.legal-li {
  display: flex;
  align-items: flex-start;
  margin-bottom: 8px;
}

.legal-dot {
  font-size: 13px;
  line-height: 22px;
  color: $primary-color;
  margin-right: 6px;
}

.legal-li-text {
  flex: 1;
  font-size: 13px;
  line-height: 22px;
  color: $text-secondary;
}

.legal-end {
  text-align: center;
  font-size: 12px;
  color: $text-muted;
  padding: 4px 0 20px;
}
</style>
