export type ProductKey = 'general' | 'shenlun' | 'theory'

const SUPPORTED_PRODUCT_KEYS: ProductKey[] = ['general', 'shenlun', 'theory']

function normalizeProductKey(value: string): ProductKey {
  const key = value.trim().toLowerCase() as ProductKey
  return SUPPORTED_PRODUCT_KEYS.includes(key) ? key : 'general'
}

/** 当前构建对应的产品；未配置时保持综合版兼容。 */
export const CURRENT_PRODUCT_KEY = normalizeProductKey(
  typeof PRODUCT_KEY === 'undefined' ? 'general' : PRODUCT_KEY,
)

export const IS_SHENLUN_PRODUCT = CURRENT_PRODUCT_KEY === 'shenlun'
export const IS_THEORY_PRODUCT = CURRENT_PRODUCT_KEY === 'theory'

export const LOCAL_PRODUCT_DEFAULTS = {
  general: { name: '知行公考', shortName: '知行', themeKey: 'red', homeMode: 'dashboard', dailyTargetMin: 30 },
  shenlun: { name: '知行申论', shortName: '申论', themeKey: 'red', homeMode: 'daily_training', dailyTargetMin: 15 },
  theory: { name: '知行政治理论', shortName: '政治理论', themeKey: 'blue', homeMode: 'daily_pack', dailyTargetMin: 15 },
} as const
