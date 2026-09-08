export interface MindMapNode {
  id: string
  title: string
  content?: string
  children?: MindMapNode[]
}

export interface ArticleSection {
  id: string
  title: string
  level: 1 | 2 | 3
  content?: string
  highlight?: string
  children?: ArticleSection[]
}

export interface Article {
  id: string
  title: string
  source: string
  publishDate: string
  summary: string
  sections: ArticleSection[]
  content: string
  tags: string[]
  mindMap: MindMapNode
}

export interface KnowledgeNode {
  id: string
  treeKey: string
  parentId: string | null
  title: string
  content: string
  myNote: string
  isStarred: boolean
  depth: number
  sortOrder: number
  path: string
  sourceFile?: string
  children: KnowledgeNode[] | null
}

export interface KnowledgeTree {
  treeKey: string
  title: string
  nodes: KnowledgeNode[]
}

export interface CorpusItem {
  id: string
  original: string
  kind: string
  sourceType: string
  sourceTitle: string
  tags: string[]
  plainNote: string
  rewrite: string
  practice: string
  status: string
  usedCount: number
  promotedTermId: string | null
  knowledgeNodeId?: string | null
  knowledgeTreeKey?: string
  knowledgePath?: string
  createdAt: string
  updatedAt: string
}

export interface CorpusStats {
  inboxCount: number
  clarifiedCount: number
  ownedCount: number
  usedCount: number
  total: number
  kinds: string[]
  sourceTypes: string[]
  tagPresets: string[]
}

export type QuizMode = 'daily' | 'article' | 'random' | 'timeline' | 'key' | 'wrong'

export interface Question {
  id: string
  articleId: string
  type: 'single' | 'multiple' | 'judge'
  stem: string
  options?: string[]
  correctAnswer: string | string[]
  analysis: string
  sourceSentence: string
}

export interface StudyRecord {
  articleId: string
  studyDate: string
  reviewCount: number
  lastReviewDate?: string
  mastered: boolean
  updatedAt?: string
}

export interface ReviewTask {
  id: string
  articleId: string
  articleTitle: string
  reviewIndex: number
  dueDate: string
  urgency: number
  type: 'article' | 'question'
}

export interface QuizAnswerRecord {
  correct: boolean
  analysis: string
  userAnswer: string | string[]
}

export interface WrongQuestionRecord {
  question: Question
  wrongCount: number
  lastWrongAt: string
  userAnswer?: string | string[]
  articleTitle: string
  tag: string
  reviewStage?: number
  nextReviewAt?: string | null
  due?: boolean
}

export interface QuizCompleteResult {
  rank: number
  totalParticipants: number
  accuracy: number
  bestAccuracy?: number
}
