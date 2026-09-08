import http, { getData } from './http'

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
  sourceFile: string
  children?: KnowledgeNode[] | null
}

export interface KnowledgeTree {
  treeKey: string
  title: string
  nodes: KnowledgeNode[]
}

export interface KnowledgeStatus {
  kb_dir: string
  kb_exists: boolean
  local_kb_dir: string
  tree_counts: Record<string, number>
  tree_titles: Record<string, string>
}

export function fetchKnowledgeTrees() {
  return getData<KnowledgeTree[]>(http.get('/admin/knowledge/trees'))
}

export function fetchKnowledgeTree(treeKey: string) {
  return getData<KnowledgeTree>(http.get(`/admin/knowledge/tree/${treeKey}`))
}

export function fetchKnowledgeStatus() {
  return getData<KnowledgeStatus>(http.get('/admin/knowledge/status'))
}

export function syncKnowledge(treeKey?: string) {
  const url = treeKey ? `/admin/knowledge/sync?tree_key=${treeKey}` : '/admin/knowledge/sync'
  return getData<Record<string, number>>(http.post(url))
}

export function uploadKnowledgeMd(file: File, sync = true) {
  const form = new FormData()
  form.append('file', file)
  return getData<{ savedPath: string; treeKey: string; sync: Record<string, number> }>(
    http.post(`/admin/knowledge/upload-md?sync=${sync}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  )
}

export function createKnowledgeNode(data: { treeKey: string; parentId?: string | null; title: string; content?: string }) {
  return getData<KnowledgeNode>(http.post('/admin/knowledge/node', data))
}

export function updateKnowledgeNode(id: string, data: { title?: string; content?: string; myNote?: string; isStarred?: boolean }) {
  return getData<KnowledgeNode>(http.put(`/admin/knowledge/node/${id}`, data))
}

export function deleteKnowledgeNode(id: string) {
  return getData<{ ok: boolean }>(http.delete(`/admin/knowledge/node/${id}`))
}

export function deleteKnowledgeTree(treeKey: string) {
  return getData<{ ok: boolean; deleted: number }>(http.delete(`/admin/knowledge/tree/${treeKey}`))
}
