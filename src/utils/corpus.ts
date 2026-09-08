export const CORPUS_KINDS_FALLBACK = ['词', '专名', '成语', '诗典', '短语', '句', '结构']
export const CORPUS_SOURCE_TYPES_FALLBACK = ['报纸', '视频', '播客', '书', '聊天', '其他']
export const CORPUS_TAG_PRESETS_FALLBACK = [
  '民生',
  '治理',
  '收束',
  '过渡',
  '对比',
  '金句',
  '问题',
  '对策',
  '其他',
]

export const CORPUS_STATUS_LABEL: Record<string, string> = {
  inbox: '待内化',
  clarified: '已澄清',
  owned: '已占有',
  used: '已运用',
}

export function corpusStatusLabel(status: string) {
  return CORPUS_STATUS_LABEL[status] || status
}

/** 按文长粗判类型，编辑页可再改（短选中偏专名/词，长选中偏句） */
export function guessCorpusKind(text: string): string {
  const t = (text || '').trim()
  if (!t) return '词'
  if (/[。！？；\n]/.test(t) || t.length > 24) return '句'
  if (t.length === 4 && !/[，、\s]/.test(t)) return '成语'
  if (t.length <= 16) return '专名'
  return '词'
}

export function buildCorpusEditUrl(opts: {
  original?: string
  kind?: string
  sourceType?: string
  sourceTitle?: string
  plainNote?: string
}): string {
  const q: string[] = []
  const push = (k: string, v?: string) => {
    const s = (v || '').trim()
    if (!s) return
    q.push(`${encodeURIComponent(k)}=${encodeURIComponent(s)}`)
  }
  push('original', opts.original)
  push('kind', opts.kind)
  push('sourceType', opts.sourceType)
  push('sourceTitle', opts.sourceTitle)
  push('plainNote', opts.plainNote)
  return q.length ? `/pages/corpus/edit?${q.join('&')}` : '/pages/corpus/edit'
}
