<template>
  <view class="brand-logo" :class="[`size-${size}`, { light }]">
    <image class="brand-logo__img" :src="logoSrc" mode="aspectFit" />
    <view v-if="showText" class="brand-logo__text">
      <text class="brand-logo__name">
        {{ APP_NAME }}
      </text>
      <text v-if="tagline" class="brand-logo__tagline">
        {{ tagline }}
      </text>
    </view>
  </view>
</template>

<script setup lang="ts">
import logoSrc from '@/assets/logo/logo.png'
import { APP_NAME } from '@/constants/brand'

withDefaults(
  defineProps<{
    size?: 'sm' | 'md' | 'lg'
    showText?: boolean
    tagline?: string
    light?: boolean
  }>(),
  {
    size: 'md',
    showText: true,
    tagline: '',
    light: false,
  },
)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.brand-logo {
  display: flex;
  align-items: center;
  gap: 12px;

  &__img {
    flex-shrink: 0;
    border-radius: 18%;
  }

  &__text {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  &__name {
    font-weight: 700;
    color: $primary-color;
    line-height: 1.2;
  }

  &__tagline {
    font-size: 12px;
    color: $text-secondary;
    line-height: 1.3;
  }

  &.light {
    .brand-logo__name,
    .brand-logo__tagline {
      color: #fff;
    }
    .brand-logo__tagline {
      opacity: 0.85;
    }
  }

  &.size-sm {
    gap: 8px;
    .brand-logo__img {
      width: 36px;
      height: 36px;
    }
    .brand-logo__name {
      font-size: 16px;
    }
  }

  &.size-md {
    .brand-logo__img {
      width: 52px;
      height: 52px;
    }
    .brand-logo__name {
      font-size: 22px;
    }
  }

  &.size-lg {
    gap: 14px;
    .brand-logo__img {
      width: 64px;
      height: 64px;
    }
    .brand-logo__name {
      font-size: 28px;
    }
    .brand-logo__tagline {
      font-size: 13px;
    }
  }
}
</style>
