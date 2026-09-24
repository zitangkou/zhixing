export type ProductKey = 'general'

/** 当前构建对应的产品；综合版固定为 general。 */
export const CURRENT_PRODUCT_KEY: ProductKey = 'general'

export const LOCAL_PRODUCT_DEFAULTS = {
  general: { name: '杜衡阁', shortName: '杜衡', themeKey: 'red', homeMode: 'dashboard', dailyTargetMin: 30 },
} as const
