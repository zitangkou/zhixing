import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createPersistedState } from 'pinia-plugin-persistedstate'
import '@nutui/nutui-taro/dist/style.css'
import '@nutui/icons-vue-taro/dist/style_iconfont.css'
import './app.scss'
import { bootstrapApp } from '@/utils/bootstrap'
import { guardGuestRoute, installNavGuards } from '@/utils/authGuard'
import { useSettingsStore } from '@/store/settings'
import { useProductStore } from '@/store/product'
import { applyTheme } from '@/utils/theme'
import { ensureFeedbackHost } from '@/utils/feedbackHost'
import { piniaPersistStorage, readPersistJson } from '@/utils/persistStorage'
import { DEFAULT_BRAND_THEME, type BrandThemeId } from '@/constants/theme'

/** 尽早读本地偏好，减少首屏闪白 */
function applyThemeFromStorage() {
  const data = readPersistJson('settings')
  if (!data) return
  const brand = (data.brandTheme as BrandThemeId | undefined) ?? DEFAULT_BRAND_THEME
  if (data.darkMode || data.brandTheme) {
    applyTheme(!!data.darkMode, brand)
  }
}
applyThemeFromStorage()
installNavGuards()

const pinia = createPinia()
pinia.use(
  createPersistedState({
    storage: piniaPersistStorage,
  }),
)

const App = createApp({
  onShow() {
    useSettingsStore().hydrateTheme()
    ensureFeedbackHost()
    void useProductStore().loadPublicConfig()
    bootstrapApp()
    guardGuestRoute()
  },
})

// H5 尽早挂载反馈层，避免首屏 toast 落到原生难看实现
ensureFeedbackHost()

App.use(pinia)

export default App
