import * as d from '../_shared'

export const apiPlan = {
  // ===== 每日学习清单 =====

  getTodayPlan(): Promise<d.ApiRes<d.DayPlan>> {
    return d.isMock ? d.mockService.getTodayPlan() : d.request('/api/plan/today')
  },

  getDayPlan(date: string): Promise<d.ApiRes<d.DayPlan>> {
    return d.isMock ? d.mockService.getDayPlan(date) : d.request(`/api/plan/day/${date}`)
  },

  getWeekPlan(): Promise<d.ApiRes<d.DayPlan[]>> {
    return d.isMock ? d.mockService.getWeekPlan() : d.request('/api/plan/week')
  },

  updatePlanTask(
    taskId: string,
    data: { status?: string; actualMinutes?: number; note?: string },
  ): Promise<d.ApiRes<d.PlanTask>> {
    return d.isMock
      ? d.mockService.updatePlanTask(taskId, data)
      : d.request(`/api/plan/task/${taskId}`, { method: 'PUT', data })
  },

  addPlanTask(data: {
    planDate: string
    timeSlot?: string
    subject?: string
    content: string
    expectedMinutes?: number
  }): Promise<d.ApiRes<d.PlanTask>> {
    return d.isMock
      ? d.mockService.addPlanTask(data)
      : d.request('/api/plan/task', { method: 'POST', data })
  },

  deletePlanTask(taskId: string): Promise<d.ApiRes<{ ok: boolean }>> {
    return d.isMock
      ? d.mockService.deletePlanTask(taskId)
      : d.request(`/api/plan/task/${taskId}`, { method: 'DELETE' })
  },

  upsertReview(data: {
    reviewDate: string
    completion?: number
    totalMinutes?: number
    weakPoint?: string
    tomorrowFocus?: string
    mood?: d.DailyReview['mood']
    note?: string
  }): Promise<d.ApiRes<d.DailyReview>> {
    return d.isMock
      ? d.mockService.upsertReview(data)
      : d.request('/api/plan/review', { method: 'POST', data })
  },
}
