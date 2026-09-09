import type { Article, ArticleSection } from '@/types'

/** 递归收集所有小节（含中间节点） */
export function flattenSections(sections: ArticleSection[]): ArticleSection[] {
  const result: ArticleSection[] = []
  for (const s of sections) {
    result.push(s)
    if (s.children?.length) {
      result.push(...flattenSections(s.children))
    }
  }
  return result
}

/** 仅含正文的小节（用于统计阅读进度） */
export function getReadableSections(sections: ArticleSection[]): ArticleSection[] {
  return flattenSections(sections).filter((s) => !!s.content?.trim())
}

/** 将多层级小节合并为纯文本（兼容出题、搜索） */
export function sectionsToContent(sections: ArticleSection[]): string {
  return getReadableSections(sections)
    .map((s) => s.content!.trim())
    .join('\n\n')
}

/** 获取文章全文：优先 sections，回退 content */
export function getArticleFullContent(article: Pick<Article, 'content' | 'sections'>): string {
  if (article.sections?.length) {
    return sectionsToContent(article.sections)
  }
  return article.content
}

/** 一级章节列表（用于目录导航） */
export function getTopLevelSections(sections: ArticleSection[]): ArticleSection[] {
  return sections.filter((s) => s.level === 1)
}

/** 统计各级小节数量 */
export function countSections(sections: ArticleSection[]): {
  total: number
  readable: number
  levels: Record<number, number>
} {
  const all = flattenSections(sections)
  const readable = getReadableSections(sections)
  const levels: Record<number, number> = {}
  for (const s of all) {
    levels[s.level] = (levels[s.level] || 0) + 1
  }
  return { total: all.length, readable: readable.length, levels }
}

const GENERIC_SECTION_TITLE =
  /^（[\d一二三四五六七八九十]+）$|^章节导言$|^第[\d一二三四]+段$|^要点\d+$/

const HTML_TAG_RE = /<(p|div|section|article|html|body|h[1-6]|table|blockquote)\b/i
const ESCAPED_HTML_TAG_RE = /&lt;(p|div|section|article|html|body|h[1-6]|table|blockquote)\b/i

export function looksLikeHtml(raw: string | undefined | null): boolean {
  const text = (raw || '').trim()
  return !!text && (HTML_TAG_RE.test(text) || ESCAPED_HTML_TAG_RE.test(text))
}

export function unescapeHtmlIfNeeded(raw: string): string {
  const text = (raw || '').trim()
  if (!text) return ''
  if (HTML_TAG_RE.test(text)) return text
  if (!ESCAPED_HTML_TAG_RE.test(text)) return text
  return text.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&')
}

export function wrapHtmlDocument(raw: string): string {
  const html = unescapeHtmlIfNeeded(raw)
  if (!html) return ''
  if (/<html[\s>]/i.test(html)) return html
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>${html}</body></html>`
}

/** 去掉 html/head，只留可塞进当前页的片段 */
export function htmlToFragment(raw: string): string {
  const html = unescapeHtmlIfNeeded(raw)
  if (!html) return ''
  const body = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i)
  if (body) return body[1].trim()
  return html
    .replace(/<head[\s\S]*?<\/head>/i, '')
    .replace(/<!DOCTYPE[^>]*>/i, '')
    .replace(/<\/?html[^>]*>/gi, '')
    .replace(/<\/?body[^>]*>/gi, '')
    .trim()
}

export function articleDisplayHtml(article: Pick<Article, 'content' | 'contentHtml'>): string {
  const html = (article.contentHtml || '').trim()
  if (html) return unescapeHtmlIfNeeded(html)
  if (looksLikeHtml(article.content)) return unescapeHtmlIfNeeded(article.content)
  return ''
}

/** 从正文首句或要点生成可读小节标题 */
export function deriveSectionTitle(section: ArticleSection): string {
  const raw = section.title.trim()
  if (!GENERIC_SECTION_TITLE.test(raw) && raw.length > 6) return raw

  const text = (section.content || section.highlight || '').trim()
  if (!text) return raw

  const numPrefix = raw.match(/^（[\d]+）/)?.[0] || ''
  let first = text.split(/[。；\n]/)[0].trim()
  first = first.replace(/^（\d+）\s*/, '').replace(/^——\s*/, '')

  if (first.length > 40) first = `${first.slice(0, 40)}…`
  if (!first) return raw
  return numPrefix ? `${numPrefix}${first}` : first
}

function enrichSectionTitles(sections: ArticleSection[]): ArticleSection[] {
  return sections.map((section) => ({
    ...section,
    title: deriveSectionTitle(section),
    children: section.children?.length ? enrichSectionTitles(section.children) : undefined,
  }))
}

/** API 返回缺少 sections 时，按段落自动拆分；已有 sections 则补充可读标题 */
export function normalizeArticle(article: Article): Article {
  if (article.contentHtml?.trim() || looksLikeHtml(article.content)) {
    return {
      ...article,
      contentHtml: articleDisplayHtml(article) || article.contentHtml,
      sections: article.sections?.length ? enrichSectionTitles(article.sections) : [],
    }
  }
  if (article.sections?.length) {
    return { ...article, sections: enrichSectionTitles(article.sections) }
  }
  const paragraphs = article.content.split(/\n\s*\n+/).filter((p) => p.trim().length > 8)
  if (!paragraphs.length) return { ...article, sections: [] }
  const sections: ArticleSection[] = [
    {
      id: 'auto-1',
      title: '正文',
      level: 1,
      children: paragraphs.map((p, i) => ({
        id: `auto-1-${i + 1}`,
        title: `（${i + 1}）`,
        level: 2 as const,
        content: p.trim(),
      })),
    },
  ]
  return { ...article, sections: enrichSectionTitles(sections) }
}
