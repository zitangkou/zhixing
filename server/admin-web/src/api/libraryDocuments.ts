import http, { getData } from './http'

export interface LibraryDocument {
  id: string
  fileName: string
  title: string
  category: string
  description: string
  format: string
  contentType: string
  fileSize: number
  sha256: string
  extractionStatus: string
  extractionError: string
  isPublished: boolean
  createdAt: string
}

export function fetchLibraryDocuments() {
  return getData<LibraryDocument[]>(http.get('/admin/library-documents'))
}

export function uploadLibraryDocument(file: File, metadata: { title: string; category: string; description: string }) {
  const form = new FormData()
  form.append('file', file)
  form.append('title', metadata.title)
  form.append('category', metadata.category)
  form.append('description', metadata.description)
  return getData<LibraryDocument>(
    http.post('/admin/library-documents', form, { headers: { 'Content-Type': 'multipart/form-data' } }),
  )
}

export function updateLibraryDocument(id: string, data: Partial<Pick<LibraryDocument, 'title' | 'category' | 'description' | 'isPublished'>>) {
  return getData<LibraryDocument>(http.patch(`/admin/library-documents/${encodeURIComponent(id)}`, data))
}

export function deleteLibraryDocument(id: string) {
  return getData<{ id: string; deleted: boolean }>(http.delete(`/admin/library-documents/${encodeURIComponent(id)}`))
}
