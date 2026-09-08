/**
 * 品牌主题色元数据（唯一真值源）。
 * 与 src/styles/variables.scss 的 $brand-themes 保持一致；JS 侧取色统一走 brandPrimary()。
 */

export type BrandThemeId = 'blue' | 'red' | 'green' | 'violet' | 'amber'

export interface BrandThemeScale {
  primary: string
  mid: string
  dark: string
}

export interface BrandThemeDef {
  id: BrandThemeId
  name: string
  light: BrandThemeScale
  dark: BrandThemeScale
}

export const BRAND_THEMES: Record<BrandThemeId, BrandThemeDef> = {
  blue: {
    id: 'blue',
    name: '深蓝',
    light: { primary: '#1e3a5f', mid: '#182b44', dark: '#142940' },
    dark: { primary: '#3d5a7a', mid: '#4a6a8e', dark: '#5a7a9e' },
  },
  red: {
    id: 'red',
    name: '中国红',
    light: { primary: '#d0021b', mid: '#a80116', dark: '#8b0000' },
    dark: { primary: '#e85d6a', mid: '#c44a56', dark: '#8f2f3a' },
  },
  green: {
    id: 'green',
    name: '墨绿',
    light: { primary: '#0f7d4f', mid: '#0b6540', dark: '#084c31' },
    dark: { primary: '#3dba80', mid: '#2f9c68', dark: '#237a51' },
  },
  violet: {
    id: 'violet',
    name: '靛紫',
    light: { primary: '#5b3a8e', mid: '#472d72', dark: '#352258' },
    dark: { primary: '#8b7bd8', mid: '#6f5fc0', dark: '#56479a' },
  },
  amber: {
    id: 'amber',
    name: '琥珀橙',
    light: { primary: '#a26500', mid: '#825000', dark: '#653c00' },
    dark: { primary: '#e0a84a', mid: '#c48f38', dark: '#9c6f2a' },
  },
}

export const BRAND_THEME_ORDER: BrandThemeId[] = ['red', 'blue', 'green', 'violet', 'amber']

export const DEFAULT_BRAND_THEME: BrandThemeId = 'red'

/** 兜底解析，非法/空 id 回退深蓝 */
export function getBrandTheme(id?: BrandThemeId | string): BrandThemeDef {
  return BRAND_THEMES[id as BrandThemeId] ?? BRAND_THEMES.blue
}

/** 当前态（亮/暗）品牌主色 hex */
export function brandPrimary(dark: boolean, id?: BrandThemeId | string): string {
  return (dark ? getBrandTheme(id).dark : getBrandTheme(id).light).primary
}
