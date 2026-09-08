import { REVIEW_INTERVALS } from '@/constants'
import type { Article, ReviewTask, StudyRecord } from '@/types'

/** 格式化日期 YYYY-MM-DD */
export function formatDate(date: Date = new Date()): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/** 解析日期字符串 */
export function parseDate(dateStr: string): Date {
  const [y, m, d] = dateStr.split('-').map(Number)
  return new Date(y, m - 1, d)
}

/** 日期差（天） */
export function daysBetween(from: string, to: string): number {
  const a = parseDate(from).getTime()
  const b = parseDate(to).getTime()
  return Math.round((b - a) / (1000 * 60 * 60 * 24))
}

/** 日期加减天数 */
export function addDays(dateStr: string, days: number): string {
  const d = parseDate(dateStr)
  d.setDate(d.getDate() + days)
  return formatDate(d)
}

/**
 * 根据艾宾浩斯间隔返回下次复习日期
 * reviewCount: 已完成复习次数（0=刚学完）
 */
export function getNextReviewDate(studyDate: string, reviewCount: number): string | null {
  if (reviewCount >= REVIEW_INTERVALS.length) return null
  const interval = REVIEW_INTERVALS[reviewCount]
  return addDays(studyDate, interval)
}

/**
 * 遍历已学文章，筛选需复习项
 */
export function generateReviewTasks(
  studiedArticles: StudyRecord[],
  articles: Article[],
  today: string = formatDate(),
): ReviewTask[] {
  const tasks: ReviewTask[] = []
  const articleMap = new Map(articles.map((a) => [a.id, a]))

  for (const record of studiedArticles) {
    if (record.mastered) continue
    const article = articleMap.get(record.articleId)
    if (!article) continue

    const nextDate = getNextReviewDate(record.studyDate, record.reviewCount)
    if (!nextDate) continue

    if (nextDate <= today) {
      const overdue = daysBetween(nextDate, today)
      tasks.push({
        id: `review-${record.articleId}-${record.reviewCount}`,
        articleId: record.articleId,
        articleTitle: article.title,
        reviewIndex: record.reviewCount,
        dueDate: nextDate,
        urgency: overdue + REVIEW_INTERVALS[record.reviewCount],
        type: 'article',
      })
    }
  }

  return tasks.sort((a, b) => b.urgency - a.urgency)
}

/** 计算连续签到天数 */
export function calcSignStreak(signStatus: Record<string, boolean>, today: string): number {
  let streak = 0
  let current = today
  while (signStatus[current]) {
    streak++
    current = addDays(current, -1)
  }
  return streak
}
