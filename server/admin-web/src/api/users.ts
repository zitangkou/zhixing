import http, { getData } from './http'
import type { AppUser, PageResult } from '@/types'

export function fetchUsers(params?: { page?: number; page_size?: number }) {
  return getData<PageResult<AppUser>>(http.get('/admin/users', { params }))
}

export function updateUser(id: string, data: Record<string, unknown>) {
  return getData<AppUser>(http.put(`/admin/users/${id}`, data))
}
