/**
 * 北京时间（UTC+8）日历日期工具。
 *
 * 业务日期（开采日、计划日、错题复习日等）一律按北京时间判断，与设备时区无关。
 * 不要用 `new Date().toISOString().slice(0, 10)`：那是 UTC 日期，北京时间 0–8 点会得到「昨天」。
 */

const BJ_OFFSET_MS = 8 * 60 * 60 * 1000

const pad2 = (n: number) => String(n).padStart(2, '0')

/** 把任意时间点格式化为北京时间 YYYY-MM-DD */
export function formatDateBJ(d: Date | number = Date.now()): string {
  const ms = typeof d === 'number' ? d : d.getTime()
  const bj = new Date(ms + BJ_OFFSET_MS)
  return `${bj.getUTCFullYear()}-${pad2(bj.getUTCMonth() + 1)}-${pad2(bj.getUTCDate())}`
}

/** 今天（北京时间）YYYY-MM-DD */
export function todayBJ(): string {
  return formatDateBJ(Date.now())
}
