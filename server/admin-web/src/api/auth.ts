import http, { getData } from './http'
import type { AdminToken, AdminUser } from '@/types'

export function login(username: string, password: string) {
  return getData<AdminToken>(
    http.post('/admin/auth/login', { username, password }),
  )
}

export function fetchMe() {
  return getData<AdminUser>(http.get('/admin/auth/me'))
}
