import type { Article, RmrbArticle } from '@/types'

export function rmrbToCard(item: RmrbArticle): Article {
  return {
    id: item.id,
    title: item.title,
    source: item.source || '人民时评',
    publishDate: item.publishDate,
    summary: item.summary || '',
    sections: [],
    content: '',
    tags: item.tags || [],
    mindMap: { id: item.id, title: item.title },
  }
}
