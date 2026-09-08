import http, { getData } from './http'

export interface PlanTemplate {
  id: string
  dayType: string  // mon/tue/wed/thu/fri/sat/sun
  timeSlot: string
  subject: string
  content: string
  priority: number
  expectedMinutes: number
  sortOrder: number
  isActive: boolean
}

export function fetchPlanTemplates(dayType?: string) {
  const url = dayType ? `/admin/plan/templates?day_type=${dayType}` : '/admin/plan/templates'
  return getData<PlanTemplate[]>(http.get(url))
}

export function copyPlanDay(fromDay: string, toDay: string, replace = true) {
  return getData<{
    ok: boolean
    fromDay: string
    toDay: string
    deleted: number
    inserted: number
  }>(http.post(`/admin/plan/templates/copy-day?from_day=${fromDay}&to_day=${toDay}&replace=${replace}`))
}

export function syncPlanPending(dayType?: string, horizonDays = 14) {
  const q = new URLSearchParams()
  if (dayType) q.set('day_type', dayType)
  q.set('horizon_days', String(horizonDays))
  return getData<{
    ok: boolean
    dayType: string
    fromDate: string
    toDate: string
    deletedTasks: number
    skippedDaysWithDone: number
    datesTouched: string[]
  }>(http.post(`/admin/plan/templates/sync-pending?${q.toString()}`))
}

export function createPlanTemplate(data: {
  dayType: string
  timeSlot?: string
  subject?: string
  content: string
  priority?: number
  expectedMinutes?: number
  sortOrder?: number
}) {
  return getData<PlanTemplate>(http.post('/admin/plan/template', data))
}

export function updatePlanTemplate(id: string, data: Partial<PlanTemplate>) {
  return getData<PlanTemplate>(http.put(`/admin/plan/template/${id}`, data))
}

export function deletePlanTemplate(id: string) {
  return getData<{ ok: boolean }>(http.delete(`/admin/plan/template/${id}`))
}
