const DAY_MS = 24 * 60 * 60 * 1000

function parseDate(value?: string): number | null {
  if (!value) return null
  const t = Date.parse(value.length <= 10 ? `${value}T00:00:00` : value)
  return Number.isNaN(t) ? null : t
}

export function isSameCalendarDay(value: string, now = new Date()): boolean {
  const t = parseDate(value)
  if (t == null) return false
  const d = new Date(t)
  return (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  )
}

export function isWithinDays(value: string, days: number, now = new Date()): boolean {
  const t = parseDate(value)
  if (t == null) return false
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  return t >= start - (days - 1) * DAY_MS && t <= start + DAY_MS
}

/** 优先当天；不足 minCount 篇则用近 days 天补齐 */
export function pickRecentFeed<T>(
  items: T[],
  getDate: (item: T) => string,
  options?: { minCount?: number; days?: number },
): { items: T[]; usedWeek: boolean } {
  const minCount = options?.minCount ?? 3
  const days = options?.days ?? 7
  const today = items.filter((item) => isSameCalendarDay(getDate(item)))
  if (today.length >= minCount) return { items: today, usedWeek: false }
  const week = items.filter((item) => isWithinDays(getDate(item), days))
  const pool = week.length ? week : items
  return { items: pool, usedWeek: today.length < minCount }
}
