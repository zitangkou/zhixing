import Taro from '@tarojs/taro'
import {
  BRAND_THEME_ORDER,
  DEFAULT_BRAND_THEME,
  brandPrimary,
  getBrandTheme,
  type BrandThemeId,
} from '@/constants/theme'
import { useSettingsStore } from '@/store/settings'

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

type Surface = Record<string, string>

const LIGHT_SURFACE: Surface = {
  '--zk-text-primary': '#1a1a1a',
  '--zk-text-secondary': '#666666',
  '--zk-text-muted': '#999999',
  '--zk-page-bg': '#f3f4f6',
  '--zk-card-bg': '#ffffff',
  '--zk-elevated': '#f7f7f8',
  '--zk-input-bg': '#ffffff',
  '--zk-border-color': '#ebebeb',
  '--zk-chip-bg': 'rgba(0, 0, 0, 0.05)',
  '--zk-hover-bg': 'rgba(0, 0, 0, 0.04)',
  '--zk-shadow-card': '0 1px 2px rgba(16, 24, 40, 0.04), 0 4px 12px rgba(16, 24, 40, 0.04)',
  '--zk-shadow-float': '0 4px 16px rgba(16, 24, 40, 0.08)',
  '--zk-tabbar-bg': '#ffffff',
  '--zk-danger-soft': '#ffebeb',
  '--zk-warn-soft': '#fff7e6',
  '--zk-success': '#07c160',
  '--zk-danger': '#ee0a24',
  '--zk-on-primary': '#ffffff',
}

const DARK_SURFACE: Surface = {
  '--zk-text-primary': '#e4e4e6',
  '--zk-text-secondary': '#a8a8ae',
  '--zk-text-muted': '#7c7c84',
  '--zk-page-bg': '#121214',
  '--zk-card-bg': '#1c1c20',
  '--zk-elevated': '#26262b',
  '--zk-input-bg': '#26262b',
  '--zk-border-color': 'rgba(255, 255, 255, 0.08)',
  '--zk-chip-bg': 'rgba(255, 255, 255, 0.07)',
  '--zk-hover-bg': 'rgba(255, 255, 255, 0.05)',
  '--zk-shadow-card': 'none',
  '--zk-shadow-float': 'none',
  '--zk-tabbar-bg': '#18181b',
  '--zk-danger-soft': 'rgba(232, 93, 106, 0.16)',
  '--zk-warn-soft': 'rgba(224, 168, 74, 0.18)',
  '--zk-success': '#3dba80',
  '--zk-danger': '#e85d6a',
  '--zk-on-primary': '#ffffff',
}

function hexRgba(hex: string, alpha: number): string {
  const h = hex.replace('#', '')
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h
  const r = parseInt(full.slice(0, 2), 16)
  const g = parseInt(full.slice(2, 4), 16)
  const b = parseInt(full.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

export type WeappPageTheme = {
  pageStyle: string
  backgroundColor: string
  backgroundColorTop: string
  backgroundColorBottom: string
  rootBackgroundColor: string
  backgroundTextStyle: 'light' | 'dark'
}

/** 写到 page-meta page-style。页面节点上的变量会盖过 wxss 里 page 的亮色兜底，并继承进子树。 */
export function buildWeappPageTheme(dark: boolean, brand: BrandThemeId = DEFAULT_BRAND_THEME): WeappPageTheme {
  const scale = dark ? getBrandTheme(brand).dark : getBrandTheme(brand).light
  const alpha = dark
    ? { light: 0.16, soft: 0.22, faint: 0.08, strong: 0.4, bar: 0.55 }
    : { light: 0.1, soft: 0.14, faint: 0.06, strong: 0.3, bar: 0.45 }
  const vars: Surface = {
    ...(dark ? DARK_SURFACE : LIGHT_SURFACE),
    '--zk-primary': scale.primary,
    '--zk-primary-mid': scale.mid,
    '--zk-primary-dark': scale.dark,
    '--zk-primary-light': hexRgba(scale.primary, alpha.light),
    '--zk-primary-soft': hexRgba(scale.primary, alpha.soft),
    '--zk-primary-faint': hexRgba(scale.primary, alpha.faint),
    '--zk-primary-strong': hexRgba(scale.primary, alpha.strong),
    '--zk-primary-bar': hexRgba(scale.primary, alpha.bar),
  }
  const pageBg = vars['--zk-page-bg']
  const pageStyle = [
    ...Object.entries(vars).map(([key, value]) => `${key}:${value}`),
    'color:var(--zk-text-primary)',
    'background-color:var(--zk-page-bg)',
  ].join(';')
  return {
    pageStyle,
    backgroundColor: pageBg,
    backgroundColorTop: pageBg,
    backgroundColorBottom: pageBg,
    rootBackgroundColor: pageBg,
    backgroundTextStyle: dark ? 'light' : 'dark',
  }
}

type WxPage = { setData?: (data: Record<string, unknown>) => void }

function pushWeappPageTheme(dark: boolean, brand: BrandThemeId) {
  if (process.env.TARO_ENV !== 'weapp') return
  const data = { zkTheme: buildWeappPageTheme(dark, brand) }
  const pages = (typeof Taro.getCurrentPages === 'function' ? Taro.getCurrentPages() : []) as WxPage[]
  for (const page of pages) page.setData?.(data)
}

function installWeappPageThemeHook() {
  if (process.env.TARO_ENV !== 'weapp') return
  const g = globalThis as typeof globalThis & {
    Page?: (config: Record<string, unknown>) => unknown
    __zkPageThemeHook?: boolean
  }
  if (g.__zkPageThemeHook || typeof g.Page !== 'function') return
  g.__zkPageThemeHook = true
  const raw = g.Page
  g.Page = (config) => {
    const userLoad = config.onLoad as ((this: WxPage, ...args: unknown[]) => unknown) | undefined
    const userShow = config.onShow as ((this: WxPage, ...args: unknown[]) => unknown) | undefined
    const paint = function (this: WxPage) {
      const settings = useSettingsStore()
      this.setData?.({ zkTheme: buildWeappPageTheme(!!settings.darkMode, settings.brandTheme) })
      return settings
    }
    config.onLoad = function (this: WxPage, ...args: unknown[]) {
      paint.call(this)
      return userLoad?.apply(this, args)
    }
    config.onShow = function (this: WxPage, ...args: unknown[]) {
      const settings = paint.call(this)
      applyTheme(!!settings.darkMode, settings.brandTheme)
      return userShow?.apply(this, args)
    }
    return raw(config)
  }
}

/** 应用「品牌主题 × 深色/浅色」到 DOM、页面根节点与原生壳 */
export function applyTheme(dark: boolean, brand: BrandThemeId = DEFAULT_BRAND_THEME) {
  setDomTheme(dark, brand)
  setNativeChrome(dark, brand)
  pushWeappPageTheme(dark, brand)
}

installWeappPageThemeHook()
