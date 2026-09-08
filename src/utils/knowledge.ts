import type { KnowledgeNode, KnowledgeTree } from '@/types'

/** 行测科目短名 → 优先匹配的知识树 tree_key */
export const SUBJECT_TREE_KEYS: Record<string, string[]> = {
  常识: ['常识判断'],
  言语: ['言语理解与表达', '言语理解'],
  数量: ['数量关系'],
  判断: ['判断推理'],
  资料: ['资料分析'],
  申论: ['申论', '申论题型'],
}

export function treeKeysForSubject(subject: string): string[] {
  return SUBJECT_TREE_KEYS[subject] || []
}

export function pickTreeForSubject(trees: KnowledgeTree[], subject: string): KnowledgeTree | null {
  const keys = treeKeysForSubject(subject)
  for (const k of keys) {
    const hit = trees.find((t) => t.treeKey === k)
    if (hit) return hit
  }
  return trees[0] || null
}

export type KnowledgePickValue = {
  nodeId: string
  treeKey: string
  path: string
}

export type FlatKnowledgeNode = {
  id: string
  treeKey: string
  title: string
  path: string
  depth: number
  hasChildren: boolean
}

/** 展平知识树，便于选择器列表展示 */
export function flattenKnowledgeNodes(tree: KnowledgeTree): FlatKnowledgeNode[] {
  const out: FlatKnowledgeNode[] = []
  const walk = (nodes: KnowledgeNode[]) => {
    for (const n of nodes) {
      const kids = n.children || []
      out.push({
        id: n.id,
        treeKey: tree.treeKey,
        title: n.title,
        path: n.path,
        depth: n.depth,
        hasChildren: kids.length > 0,
      })
      if (kids.length) walk(kids)
    }
  }
  walk(tree.nodes || [])
  return out
}

export function formatKnowledgeLabel(path: string, treeTitle?: string): string {
  if (!path) return ''
  return treeTitle ? `${treeTitle} · ${path.replace(/\//g, ' / ')}` : path.replace(/\//g, ' / ')
}
