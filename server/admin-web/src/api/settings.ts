import http, { getData } from './http'

export interface SettingItem {
  key: string
  value: string
  description: string
}

export function fetchSettings() {
  return getData<SettingItem[]>(http.get('/admin/settings'))
}

export function updateSetting(key: string, value: string) {
  return getData<SettingItem>(http.put(`/admin/settings/${key}`, { value }))
}

export function fetchRoles() {
  return getData<Array<{ id: string; code: string; name: string; permissions: string[] }>>(
    http.get('/admin/roles'),
  )
}

export function fetchPermissions() {
  return getData<unknown>(http.get('/admin/permissions'))
}

export function fetchRoleMatrix() {
  return getData<Record<string, string[]>>(http.get('/admin/roles/matrix'))
}
