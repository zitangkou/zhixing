/** 人民日报三刀解剖 · 兜底常量（优先用 /api/rmrb/meta） */
export const RMRB_TERM_CATEGORIES_FALLBACK = [
  '问题与积弊',
  '治理方法与理念',
  '成效与目标',
  '发展理念',
  '战略方法',
  '资源配置',
  '目标效能',
  '基础建设',
  '问题警示',
  '其他',
] as const

export const RMRB_VERB_CATEGORIES_FALLBACK = ['治理动作', '分析评价', '动词其他'] as const

export const RMRB_TEMPLATE_TYPES_FALLBACK = [
  { value: 'dialectic', label: '对比转折型', tip: '继续沿用……，与其说是……，不如说是……。' },
  {
    value: 'direction',
    label: '排比递进型',
    tip: '……并非……，而是在既有……内把……做得更……，于细微处见真章。',
  },
  { value: 'solution', label: '条件递进型', tip: '……往……方向多走一步，……就增强几分。' },
  { value: 'quote', label: '金句型', tip: '利民之事，丝发必兴。（结尾升华）' },
] as const

export const RMRB_ARGUMENT_METHOD_PRESETS_FALLBACK = [
  {
    name: '点例排比 + 类比延伸',
    scope: 'point',
    note: '点例各一句话；3个排比；再类比到其他领域',
    template:
      '提出分论点 → 列举3个同一领域正面案例（各一句） → 提炼共性 → 类比其他2～3个领域 → 总结升华',
  },
  {
    name: '问题切入 + 典型案例深描 + 原因挖掘',
    scope: 'point',
    note: '案例稍展开：问题+做法+成效；再挖原因与对策',
    template:
      '提出分论点 → 点出问题普遍性 → 典型案例1 → 典型案例2 → 提炼共性 → 挖掘原因 → 提出对策',
  },
  {
    name: '总—分—分—总',
    scope: 'overview',
    note: '全文结构：总论点下并列分论点，收束升华',
    template: '现象引题 → 提出总论点 → 分论点1 → 分论点2 → 总结升华（金句/呼吁）',
  },
  {
    name: '金句定调 + 排比收束',
    scope: 'overview',
    note: '适合结尾或总论点后的升华段',
    template: '引用金句定调 → 从……到……排比回顾案例 → 提炼主题一句 → 展望呼吁（回扣标题）',
  },
] as const

/** 顿号/逗号等分隔的多词录入 → 拆成独立词条展示 */
export function splitRmrbTerms(raw: string): string[] {
  return String(raw || '')
    .split(/[、,，;；/｜|\n]+/)
    .map((s) => s.trim())
    .filter(Boolean)
}

/** @deprecated 请使用接口 meta；保留兼容旧引用 */
export const RMRB_TERM_CATEGORIES = RMRB_TERM_CATEGORIES_FALLBACK
export const RMRB_TEMPLATE_TYPES = RMRB_TEMPLATE_TYPES_FALLBACK
