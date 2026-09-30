import http, { getData } from './http'

export interface KnowledgeIssue {
  level: 'error' | 'warning'
  code: string
  line: number
  message: string
  path?: string
}

export interface StructuredIssue { level: 'error' | 'warning'; message: string }

export interface MapNode {
  id: string
  title: string
  content?: string
  depth: number
  line: number
  path: string
  children?: MapNode[] | null
  blocks?: KnowledgeBlock[]
  description?: string
  groups?: Array<{ title: string; nodeIds: string[] }>
}

export type KnowledgeBlock =
  | { type: 'text'; text: string }
  | { type: 'formula'; latex: string; plain: string }
  | { type: 'image'; url: string; alt?: string }
  | { type: 'example'; question: string; answer?: string }

export interface StructuredNode {
  id: string
  title: string
  blocks: KnowledgeBlock[]
  children: StructuredNode[]
}

export interface StructuredTree {
  schemaVersion: 2
  title: string
  description: string
  groups: Array<{ title: string; nodeIds: string[] }>
  children: StructuredNode[]
}

export interface KnowledgeTreeMeta {
  treeKey: string
  title: string
  sortOrder: number
  isVisible: boolean
  draftRevision: number
  draftUpdatedAt: string | null
  latestVersion: number
  liveVersion: number
  hasUnpublishedChanges: boolean
  liveNodeCount: number
  livePublishedAt: string | null
}

export interface KnowledgeDoc {
  treeKey: string
  title: string
  mdDraft: string
  draftRevision: number
  draftUpdatedAt: string | null
  draftUpdatedBy: string
  liveVersion: number
  liveMd: string
}

export interface KnowledgePreview {
  title: string
  tree: MapNode | null
  stats: { nodeCount: number; leafCount: number; maxDepth: number }
  issues: KnowledgeIssue[]
}

export interface ExportPlanSegment {
  key: string
  title: string
  rootPath: string
  nodeCount: number
}

export interface KnowledgePublishResult {
  version: number
  tree: MapNode | null
  stats: { nodeCount: number; leafCount: number; maxDepth: number }
  /** 激活后预计的节点变化（发布本身不改动节点） */
  nodeDiffPreview: { added: number; archived: number; kept: number }
  exportPlan: { segments: ExportPlanSegment[] }
  issues: KnowledgeIssue[]
}

export interface KnowledgeAsset {
  url: string
  width: number
  height: number
  bytes: number
  thumbUrl: string
  thumbWidth: number
  thumbHeight: number
  sha256: string
}

export interface KnowledgeManifest {
  version: number
  generatedAt: string
  theme: string
  scale: number
  overview?: KnowledgeAsset
  segments: Array<KnowledgeAsset & { key: string; title: string; rootPath: string; nodeCount: number }>
  svg?: { url: string; bytes: number }
  treeJsonUrl?: string
}

export interface KnowledgeVersionMeta {
  version: number
  note: string
  createdAt: string
  createdBy: string
  nodeCount: number
  assetsReady: boolean
  isLive: boolean
}

export interface KnowledgeNodeDiff {
  added: number
  archived: number
  kept: number
  moved: number
}

export function fetchKnowledgeTrees() {
  return getData<KnowledgeTreeMeta[]>(http.get('/admin/knowledge/trees'))
}

export function createKnowledgeTree(data: { treeKey: string; title: string; md?: string }) {
  return getData<KnowledgeTreeMeta>(http.post('/admin/knowledge/trees', data))
}

export function patchKnowledgeTree(
  treeKey: string,
  data: { title?: string; sortOrder?: number; isVisible?: boolean },
) {
  return getData<KnowledgeTreeMeta>(http.patch(`/admin/knowledge/trees/${encodeURIComponent(treeKey)}`, data))
}

export function deleteKnowledgeTree(treeKey: string) {
  return getData<{ ok: boolean; treeKey: string }>(
    http.delete(`/admin/knowledge/trees/${encodeURIComponent(treeKey)}`),
  )
}

export function fetchKnowledgeDoc(treeKey: string) {
  return getData<KnowledgeDoc>(http.get(`/admin/knowledge/trees/${encodeURIComponent(treeKey)}/doc`))
}

export function fetchStructuredKnowledge(treeKey: string) {
  return getData<{ tree: StructuredTree; draftRevision: number; issues: StructuredIssue[] }>(
    http.get(`/admin/knowledge/trees/${encodeURIComponent(treeKey)}/structured`),
  )
}

export function saveStructuredKnowledge(treeKey: string, tree: StructuredTree, baseRevision: number) {
  return getData<{ tree: StructuredTree; draftRevision: number; issues: StructuredIssue[] }>(
    http.put(`/admin/knowledge/trees/${encodeURIComponent(treeKey)}/structured`, { tree, baseRevision }),
  )
}

export function previewStructuredKnowledge(tree: StructuredTree, treeKey = '') {
  return getData<{ tree: MapNode; nodeDiffPreview: { added: number; archived: number; kept: number } | null; issues: StructuredIssue[]; stats: { nodeCount: number; leafCount: number; maxDepth: number } }>(
    http.post('/admin/knowledge/structured-preview', { tree, treeKey }),
  )
}

export function saveKnowledgeDoc(treeKey: string, md: string, baseRevision: number) {
  return getData<{ draftRevision: number; draftUpdatedAt: string | null; issues: KnowledgeIssue[] }>(
    http.put(`/admin/knowledge/trees/${encodeURIComponent(treeKey)}/doc`, { md, baseRevision }),
  )
}

export function previewKnowledgeMd(md: string) {
  return getData<KnowledgePreview>(http.post('/admin/knowledge/preview', { md }))
}

export function publishKnowledgeTree(treeKey: string, baseRevision: number, note = '') {
  return getData<KnowledgePublishResult>(
    http.post(`/admin/knowledge/trees/${encodeURIComponent(treeKey)}/publish`, { baseRevision, note }),
  )
}

export function uploadKnowledgeAssets(
  treeKey: string,
  version: number,
  manifest: Omit<KnowledgeManifest, 'version'>,
  files: File[],
  activate = true,
) {
  const form = new FormData()
  form.append('manifest', JSON.stringify(manifest))
  for (const f of files) {
    form.append('files', f, f.name)
  }
  const q = activate ? '' : '?activate=false'
  return getData<{
    version: number
    liveVersion: number
    manifest: KnowledgeManifest
    nodeDiff: KnowledgeNodeDiff | null
  }>(
    http.post(`/admin/knowledge/trees/${encodeURIComponent(treeKey)}/versions/${version}/assets${q}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    }),
  )
}

export function fetchKnowledgeVersions(treeKey: string) {
  return getData<KnowledgeVersionMeta[]>(
    http.get(`/admin/knowledge/trees/${encodeURIComponent(treeKey)}/versions`),
  )
}

export function fetchKnowledgeVersion(treeKey: string, version: number) {
  return getData<{
    version: number
    md: string
    manifest: KnowledgeManifest
    tree: MapNode
    assetsReady: boolean
    note: string
    createdAt: string
  }>(http.get(`/admin/knowledge/trees/${encodeURIComponent(treeKey)}/versions/${version}`))
}

export function activateKnowledgeVersion(treeKey: string, version: number, expectedLive?: number, allowNoAssets = false) {
  return getData<{ treeKey: string; liveVersion: number; previousLive: number; nodeDiff: KnowledgeNodeDiff }>(
    http.post(`/admin/knowledge/trees/${encodeURIComponent(treeKey)}/versions/${version}/activate`, {
      expectedLive,
      allowNoAssets,
    }),
  )
}

export function rollbackKnowledgeVersion(treeKey: string, version: number) {
  return getData<KnowledgeDoc>(
    http.post(`/admin/knowledge/trees/${encodeURIComponent(treeKey)}/versions/${version}/rollback`),
  )
}

export function uploadKnowledgeMd(file: File, force = false) {
  const form = new FormData()
  form.append('file', file)
  return getData<{
    savedPath: string
    treeKey: string
    import: { ok?: boolean; error?: string; unchanged?: boolean } & Record<string, unknown>
  }>(
    http.post(`/admin/knowledge/upload-md?sync=false${force ? '&force=true' : ''}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  )
}

export function uploadKnowledgeImage(file: File) {
  const data = new FormData()
  data.append('file', file)
  return getData<{ url: string }>(http.post('/admin/knowledge/upload-image', data))
}
