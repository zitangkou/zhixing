export interface RmrbArticle {
  id: string
  title: string
  source: string
  publishDate: string
  summary: string
  content: string
  /** 主题标签：政绩观、社会治理、乡村振兴等 */
  tags: string[]
  isPublished: boolean
  sortOrder: number
  readCount: number
  createdAt: string
  updatedAt: string
}

export interface ShenlunMineTermItem {
  term: string
  category: string
  plainWord: string
}

export interface ShenlunQuoteItem {
  text: string
  /** 来源，如：清代万斯大 */
  source: string
  /** 释义 */
  meaning?: string
}

export interface ShenlunVerbItem {
  verb: string
  usage: string
  category: string
}

export interface ShenlunArgumentFieldValue {
  key: string
  label: string
  content: string
}

export interface ShenlunArgumentPoint {
  /** 分论点标题 */
  title: string
  /** 旧字段，兼容读取后并入 title */
  claim: string
  /** 论据（可选） */
  evidence: string
  /** 小结（可选） */
  summary: string
  /** 论证方法名，如：时间推进法 */
  method?: string
  /** 方法说明（可选） */
  methodNote?: string
  /** 套用模板 */
  template?: string
}

export interface ShenlunArgumentSkeleton {
  templateId: string
  templateName: string
  mode: string
  /** 总论点 */
  overview: string
  /** 总结 */
  conclusion: string
  /** 总论点论证方法 */
  overviewMethod?: string
  /** 总论点论证模板 */
  overviewTemplate?: string
  fields: ShenlunArgumentFieldValue[]
  points: ShenlunArgumentPoint[]
}

export interface ShenlunTemplateItem {
  type: string
  typeName?: string
  original: string
  template: string
  imitate: string
}

export interface ShenlunSkeletonFieldDef {
  key: string
  label: string
  placeholder?: string
}

export interface ShenlunSkeletonStructure {
  mode: string
  fields: ShenlunSkeletonFieldDef[]
  overviewLabel?: string
  overviewPlaceholder?: string
  pointFields: ShenlunSkeletonFieldDef[]
}

export interface ShenlunTermCategory {
  id: string
  name: string
  kind?: 'term' | 'verb' | string
  sortOrder: number
  isEnabled: boolean
}

export interface ShenlunArgumentMethodPreset {
  id?: string
  name: string
  scope: 'overview' | 'point' | string
  note: string
  template: string
  sortOrder?: number
  isEnabled?: boolean
}

export interface ShenlunSkeletonTemplate {
  id: string
  name: string
  description: string
  mode: string
  structure: ShenlunSkeletonStructure
  sortOrder: number
  isEnabled: boolean
}

export interface ShenlunSentenceType {
  id: string
  code: string
  name: string
  tip: string
  sortOrder: number
  isEnabled: boolean
}

export interface ShenlunMeta {
  termCategories: ShenlunTermCategory[]
  verbCategories?: ShenlunTermCategory[]
  skeletonTemplates: ShenlunSkeletonTemplate[]
  sentenceTypes: ShenlunSentenceType[]
  argumentMethodPresets?: ShenlunArgumentMethodPreset[]
}

export interface ShenlunMineLog {
  id: string
  mineDate: string
  articleId: string | null
  articleTitle: string
  sourceExcerpt: string
  argumentChain: string
  templateSentence: string
  terms: ShenlunMineTermItem[]
  quotes?: ShenlunQuoteItem[]
  verbs?: ShenlunVerbItem[]
  argument: ShenlunArgumentSkeleton
  templates: ShenlunTemplateItem[]
  createdAt: string
  updatedAt: string
}

export interface ShenlunNormTerm {
  id: string
  term: string
  category: string
  usageNote: string
  sourceTitle: string
  exampleSentence: string
  articleId: string | null
  familiarity: number
  mastered: boolean
  createdAt: string
}

export interface ShenlunStats {
  weekMineDays: number
  weekMineTarget: number
  termCount: number
  learningTermCount: number
  todayMined: boolean
  weekDrillCount: number
}

export interface ShenlunDrillLog {
  id: string
  drillType: 'sentence' | 'imitate' | 'oral' | string
  content: string
  prompt: string
  refMineId: string | null
  refTermIds: string[]
  createdAt: string
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

export type CorpusStatus = 'inbox' | 'clarified' | 'owned' | 'used' | string

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
  status: CorpusStatus
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
