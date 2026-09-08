import { defineStore } from 'pinia'
import { applyTheme } from '@/utils/theme'
import { DEFAULT_BRAND_THEME, type BrandThemeId } from '@/constants/theme'

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    darkMode: false,
    brandTheme: DEFAULT_BRAND_THEME as BrandThemeId,
  }),

  actions: {
    setDarkMode(on: boolean) {
      this.darkMode = on
      applyTheme(on, this.brandTheme)
    },

    setBrandTheme(id: BrandThemeId) {
      this.brandTheme = id
      applyTheme(this.darkMode, id)
    },

    toggleDarkMode() {
      this.setDarkMode(!this.darkMode)
    },

    /** 启动时根据持久化状态套用主题 */
    hydrateTheme() {
      applyTheme(this.darkMode, this.brandTheme)
    },
  },

  persist: {
    pick: ['darkMode', 'brandTheme'],
  },
})
