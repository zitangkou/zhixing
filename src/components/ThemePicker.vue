<template>
  <nut-popup v-model:visible="visible" position="bottom" round :closeable="true">
    <view class="theme-picker">
      <text class="picker-title"> 主题色 </text>
      <view class="swatch-row">
        <view
          v-for="t in themes"
          :key="t.id"
          class="swatch"
          :class="{ active: t.id === settingsStore.brandTheme }"
          @tap="pick(t.id)"
        >
          <view class="swatch-dot" :style="{ background: t.light.primary }">
            <CheckChecked v-if="t.id === settingsStore.brandTheme" color="#fff" size="16" />
          </view>
          <text class="swatch-name">
            {{ t.name }}
          </text>
        </view>
      </view>
    </view>
  </nut-popup>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Popup as NutPopup } from '@nutui/nutui-taro'
import { CheckChecked } from '@nutui/icons-vue-taro'
import { BRAND_THEME_ORDER, BRAND_THEMES, type BrandThemeId } from '@/constants/theme'
import { useSettingsStore } from '@/store/settings'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ 'update:visible': [v: boolean] }>()

const settingsStore = useSettingsStore()
const themes = BRAND_THEME_ORDER.map((id) => BRAND_THEMES[id])

const visible = computed({
  get: () => props.visible,
  set: (v: boolean) => emit('update:visible', v),
})

function pick(id: BrandThemeId) {
  settingsStore.setBrandTheme(id)
  visible.value = false
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.theme-picker {
  padding: 20px 16px calc(16px + env(safe-area-inset-bottom));

  .picker-title {
    display: block;
    text-align: center;
    font-size: 16px;
    font-weight: 600;
    color: $text-primary;
    margin-bottom: 20px;
  }

  .swatch-row {
    display: flex;
    justify-content: space-between;
    gap: 8px;
  }

  .swatch {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    min-width: 44px;

    .swatch-dot {
      width: 44px;
      height: 44px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 2px solid transparent;
      box-sizing: border-box;
    }

    .swatch-name {
      font-size: 12px;
      color: $text-secondary;
    }

    &.active {
      .swatch-dot {
        border-color: $primary-color;
      }
      .swatch-name {
        color: $primary-color;
        font-weight: 600;
      }
    }
  }
}
</style>
