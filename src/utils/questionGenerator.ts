import { POLITICAL_KEYWORDS } from '@/constants'
import type { Article, ArticleSection, Question } from '@/types'
import { flattenSections } from '@/utils/articleContent'
// R3 停用挖空后 getArticleFullContent 暂未使用，保留 import 以便回溯
// import { flattenSections, getArticleFullContent } from '@/utils/articleContent'

const DISTRACTORS: Record<string, string[]> = {
  两个确立: ['两个维护', '四个意识', '四个自信', '四个全面'],
  两个维护: ['两个确立', '四个意识', '四个自信', '四个统一'],
  新质生产力: ['传统生产力', '全要素生产率', '数字经济', '绿色生产力'],
  中国式现代化: ['社会主义现代化', '四个现代化', '全面现代化', '新型工业化'],
  根本保证: ['基本前提', '重要保障', '有力支撑', '必然要求'],
  核心: ['关键', '重点', '中心', '枢纽'],
  本质: ['实质', '本性', '实质内涵', '根本属性'],
  根本立场: ['基本立场', '价值追求', '出发点和落脚点', '根本宗旨'],
  最大优势: ['显著优势', '制度优势', '独特优势', '核心优势'],
  必由之路: ['唯一道路', '正确道路', '根本途径', '必然选择'],
  根本方向: ['正确方向', '前进方向', '战略方向', '目标导向'],
  根本任务: ['中心任务', '首要任务', '战略任务', '历史任务'],
  鲜明特色: ['显著特点', '独特品格', '基本特征', '突出优势'],
  本质要求: ['基本要求', '内在要求', '必然要求', '核心要义'],
  战略支撑: ['重要支撑', '有力保障', '基础支撑', '关键支撑'],
  根本遵循: ['行动指南', '理论指引', '基本遵循', '重要依据'],
}

interface SectionSource {
  sectionTitle: string
  highlight?: string
  content?: string
  /** —— 子条目，如六项原则 */
  bulletItems: string[]
  /** highlight 中分号/顿号并列短语 */
  parallelItems: string[]
}

function shuffle<T>(arr: T[]): T[] {
  const copy = [...arr]
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

function unique<T>(arr: T[]): T[] {
  return [...new Set(arr)]
}

/** 从 highlight / 正文中提取分号并列的短语 */
function extractParallelItems(text: string): string[] {
  if (!text.includes('；') && !text.includes(';')) return []
  const parts = text
    .split(/[；;]/)
    .map((s) => s.trim().replace(/[。．]$/, ''))
    .filter((s) => s.length >= 8 && s.length <= 60)
  return parts.length >= 2 ? parts : []
}

/** 从 level-3 子节提取 —— 条目标签 */
function extractBulletItems(section: ArticleSection): string[] {
  if (!section.children?.length) return []
  return section.children
    .filter((c) => c.level === 3)
    .map((c) => {
      const label = c.title.replace(/[。．]$/, '').trim()
      if (label.length >= 4 && label.length <= 28) return label
      const first = c.content?.split(/[。；\n]/)[0]?.trim() || ''
      return first.slice(0, 28)
    })
    .filter((s) => s.length >= 4)
}

function collectSectionSources(sections: ArticleSection[]): SectionSource[] {
  const sources: SectionSource[] = []
  for (const section of flattenSections(sections)) {
    const bulletItems = extractBulletItems(section)
    const highlight = section.highlight?.trim()
    const parallelItems = highlight ? extractParallelItems(highlight) : []
    if (highlight || bulletItems.length >= 2 || parallelItems.length >= 2) {
      sources.push({
        sectionTitle: section.title,
        highlight,
        content: section.content?.trim(),
        bulletItems,
        parallelItems,
      })
    }
  }
  return sources
}

function allBulletPool(sources: SectionSource[]): string[] {
  return unique(sources.flatMap((s) => s.bulletItems))
}

function pickDistractors(correct: string, pool: string[], count = 3): string[] {
  const candidates = pool.filter((item) => item !== correct)
  return shuffle(candidates).slice(0, count)
}

function findKeywordInText(text: string): string | null {
  for (const kw of POLITICAL_KEYWORDS) {
    if (text.includes(kw)) return kw
  }
  return null
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars -- R3 已停用，保留函数体以便回溯
function createHighlightBlankQuestion(
  article: Article,
  text: string,
  index: number,
  context: string,
): Question | null {
  // R3: 挖空模板生成器已停用，见 xingce-data-roadmap R3
  // 保留函数体以便回溯，但任何调用都会立即抛出。
  throw new Error('挖空模板生成器已停用，见 xingce-data-roadmap R3')
  const keyword = findKeywordInText(text)
  if (!keyword) return null
  const stem = text.replace(keyword, '______')
  if (stem === text) return null
  const distractors = DISTRACTORS[keyword] || ['重要基础', '关键环节', '主要矛盾', '中心环节']
  return {
    id: `q-${article.id}-h${index}`,
    articleId: article.id,
    type: 'single',
    stem: `（单选）${stem}`,
    options: shuffle([keyword, ...distractors.slice(0, 3)]),
    correctAnswer: keyword,
    analysis: `正确答案为「${keyword}」。${context}`,
    sourceSentence: text,
  }
}

function createParallelItemQuestion(
  article: Article,
  source: SectionSource,
  item: string,
  index: number,
  allItems: string[],
): Question {
  const distractors = pickDistractors(item, allItems, 3)
  while (distractors.length < 3) {
    distractors.push(`干扰项${distractors.length + 1}`)
  }
  return {
    id: `q-${article.id}-p${index}`,
    articleId: article.id,
    type: 'single',
    stem: `（单选）下列表述中，属于「${source.sectionTitle.slice(0, 20)}」相关要点的是（ ）`,
    options: shuffle([item, ...distractors.slice(0, 3)]),
    correctAnswer: item,
    analysis: `正确答案是原文并列要点之一，需准确记忆关键表述。`,
    sourceSentence: source.highlight || item,
  }
}

function createBulletQuestion(
  article: Article,
  source: SectionSource,
  item: string,
  index: number,
  pool: string[],
): Question {
  const distractors = pickDistractors(item, pool, 3)
  return {
    id: `q-${article.id}-b${index}`,
    articleId: article.id,
    type: 'single',
    stem: `（单选）下列属于「${source.sectionTitle.replace(/^（\d+）/, '').slice(0, 24) || '本节'}」内容的是（ ）`,
    options: shuffle([item, ...distractors.slice(0, 3)]),
    correctAnswer: item,
    analysis: `该选项出自原文条目，需与相似表述区分记忆。`,
    sourceSentence: item,
  }
}

function createJudgeQuestion(
  article: Article,
  sentence: string,
  index: number,
  wrong = false,
): Question {
  if (wrong) {
    const wrongStem = sentence
      .replace(/两个确立/g, '两个统一')
      .replace(/两个维护/g, '两个确立')
      .replace(/根本/g, '基本')
      .replace(/核心/g, '关键')
      .replace(/坚持党的全面领导/g, '坚持市场决定性作用')
      .replace(/坚持人民至上/g, '坚持效率优先')
    if (wrongStem === sentence) {
      return createJudgeQuestion(article, sentence, index, false)
    }
    return {
      id: `q-${article.id}-j${index}`,
      articleId: article.id,
      type: 'judge',
      stem: `（判断）${wrongStem}`,
      options: ['正确', '错误'],
      correctAnswer: '错误',
      analysis: `该表述与原文不符。正确表述应为：${sentence}`,
      sourceSentence: sentence,
    }
  }
  return {
    id: `q-${article.id}-j${index}`,
    articleId: article.id,
    type: 'judge',
    stem: `（判断）${sentence}`,
    options: ['正确', '错误'],
    correctAnswer: '正确',
    analysis: '该表述与原文一致，判断正确。',
    sourceSentence: sentence,
  }
}

/** 从文章 sections 优先生成题目（highlight > 并列项 > 条目） */
export function generateQuestionsFromArticle(article: Article): Question[] {
  const isFeatured = Boolean(article.isFeatured)
  const maxTotal = isFeatured ? 10 : 5
  const questions: Question[] = []
  const usedStems = new Set<string>()

  const push = (q: Question | null) => {
    if (!q || questions.length >= maxTotal) return
    if (usedStems.has(q.stem)) return
    usedStems.add(q.stem)
    questions.push(q)
  }

  const sections = article.sections || []
  const sources = sections.length ? collectSectionSources(sections) : []
  const bulletPool = allBulletPool(sources)
  const parallelPool = unique(sources.flatMap((s) => s.parallelItems))

  // 1. highlight 挖空（政治术语）—— R3 已停用，见 xingce-data-roadmap R3
  // for (const source of sources) {
  //   if (!source.highlight) continue
  //   push(
  //     createHighlightBlankQuestion(
  //       article,
  //       source.highlight,
  //       questions.length,
  //       `出自「${source.sectionTitle}」要点。`,
  //     ),
  //   )
  // }

  // 2. —— 条目选择题（六项原则等）
  for (const source of sources) {
    if (source.bulletItems.length < 2) continue
    for (const item of shuffle(source.bulletItems).slice(0, 2)) {
      push(createBulletQuestion(article, source, item, questions.length, bulletPool))
    }
  }

  // 3. 分号并列短语选择题
  for (const source of sources) {
    for (const item of source.parallelItems.slice(0, 2)) {
      push(createParallelItemQuestion(article, source, item, questions.length, parallelPool))
    }
  }

  // 4. highlight 判断题（正确 + 篡改）
  for (const source of sources) {
    if (!source.highlight || source.highlight.length > 120) continue
    const sentence = source.highlight.endsWith('。') ? source.highlight : `${source.highlight}。`
    push(createJudgeQuestion(article, sentence, questions.length, false))
    push(createJudgeQuestion(article, sentence, questions.length, true))
    if (questions.length >= maxTotal) break
  }

  // 5. 兜底：全文关键词挖空 —— R3 已停用，见 xingce-data-roadmap R3
  // if (questions.length < maxTotal) {
  //   const fullContent = getArticleFullContent(article)
  //   const sentences = fullContent.split(/[。！？\n]+/).filter((s) => s.trim().length > 15)
  //   for (const sentence of sentences) {
  //     const text = sentence.trim() + '。'
  //     push(createHighlightBlankQuestion(article, text, questions.length, '出自原文关键表述。'))
  //     if (questions.length >= maxTotal) break
  //   }
  // }

  return questions.slice(0, maxTotal)
}

/** 预生成全部题库 */
export function buildQuestionBank(articles: Article[]): Map<string, Question[]> {
  const bank = new Map<string, Question[]>()
  for (const article of articles) {
    bank.set(article.id, generateQuestionsFromArticle(article))
  }
  return bank
}

/** 校验答案 */
export function checkAnswer(question: Question, answer: string | string[]): boolean {
  const correct = question.correctAnswer
  if (Array.isArray(correct)) {
    if (!Array.isArray(answer)) return false
    return correct.length === answer.length && correct.every((c) => answer.includes(c))
  }
  return answer === correct
}
