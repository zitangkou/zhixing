import { defineStore } from 'pinia'
import { api, type ProductPublicConfig } from '@/api'
import { CURRENT_PRODUCT_KEY, LOCAL_PRODUCT_DEFAULTS } from '@/constants/product'
import type { BrandThemeId } from '@/constants/theme'
import { useSettingsStore } from '@/store/settings'

const defaults = LOCAL_PRODUCT_DEFAULTS[CURRENT_PRODUCT_KEY]

function fallbackConfig(): ProductPublicConfig {
  return {
    key: CURRENT_PRODUCT_KEY,
    ...defaults,
    enabledModules: [],
    tabs: [],
  }
}

export const useProductStore = defineStore('product', {
  state: () => ({
    config: fallbackConfig(),
    allowRegister: false,
    loaded: false,
    loadError: '',
  }),

  actions: {
    async loadPublicConfig(force = false) {
      if (this.loaded && !force) return true
      const res = await api.getPublicConfig()
      if (res.code !== 0 || !res.data) {
        this.loadError = res.message || '产品配置加载失败'
        return false
      }
      this.config = res.data.product
      useSettingsStore().setBrandTheme(res.data.product.themeKey as BrandThemeId)
      this.allowRegister = res.data.allowRegister
      this.loaded = true
      this.loadError = ''
      return true
    },
  },
})
