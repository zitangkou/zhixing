import Taro from '@tarojs/taro'
import {
  BRAND_THEME_ORDER,
  DEFAULT_BRAND_THEME,
  brandPrimary,
  type BrandThemeId,
} from '@/constants/theme'

const DARK_CLASS = 'theme-dark'
const THEME_CLASSES = BRAND_THEME_ORDER.map((id) => `theme-${id}`)
const isH5 = process.env.TARO_ENV === 'h5'

function setDomTheme(dark: boolean, brand: BrandThemeId) {
  if (typeof document === 'undefined') return
  const roots = [document.documentElement, document.body, document.getElementById('app')].filter(
    Boolean,
  ) as HTMLElement[]
  for (const el of roots) {
    el.classList.toggle(DARK_CLASS, dark)
    for (const cls of THEME_CLASSES) el.classList.remove(cls)
    el.classList.add(`theme-${brand}`)
  }
}

/** 吞掉小程序专有 API 在 H5 上的 Promise 拒绝 */
function callNative(fn: () => unknown) {
  try {
    const ret = fn()
    if (ret && typeof (ret as Promise<unknown>).then === 'function') {
      (ret as Promise<unknown>).catch(() => {})
    }
  } catch {
    /* 部分环境无对应 API */
  }
}

/** 同步导航栏 / 窗口 / tabBar 背景（小程序原生；H5 仅改 DOM） */
function setNativeChrome(dark: boolean, brand: BrandThemeId) {
  const primary = brandPrimary(dark, brand)
  callNative(() =>
    Taro.setNavigationBarColor({
      frontColor: '#ffffff',
      backgroundColor: primary,
      animation: { duration: 200, timingFunc: 'easeIn' },
    }),
  )
  // tabBar 激活色跟随品牌色（H5 无原生 tabBar，靠 callNative 吞 reject）
  callNative(() =>
    Taro.setTabBarStyle({
      color: dark ? '#7c7c84' : '#999999',
      selectedColor: primary,
      backgroundColor: dark ? '#18181b' : '#ffffff',
    }),
  )
  // 下拉背景色 / 文字样式仅小程序支持，H5 会抛「暂时不支持 API」
  if (isH5) return
  callNative(() =>
    Taro.setBackgroundColor({
      backgroundColor: dark ? '#121212' : '#f3f4f6',
      backgroundColorTop: dark ? '#121212' : '#f3f4f6',
      backgroundColorBottom: dark ? '#121212' : '#f3f4f6',
    }),
  )
  callNative(() => Taro.setBackgroundTextStyle({ textStyle: dark ? 'light' : 'dark' }))
}

/** 应用「品牌主题 × 深色/浅色」到 DOM 与原生壳 */
export function applyTheme(dark: boolean, brand: BrandThemeId = DEFAULT_BRAND_THEME) {
  setDomTheme(dark, brand)
  setNativeChrome(dark, brand)
}
