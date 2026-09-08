import * as d from '../_shared'
import { CURRENT_PRODUCT_KEY } from '@/constants/product'

export const apiProduct = {
  getDailyTasks(date?: string): Promise<d.ApiRes<d.DailyTaskList>> {
    if (d.isMock) {
      const taskDate = date || new Date().toISOString().slice(0, 10)
      return Promise.resolve({
        code: 0,
        message: 'ok',
        data: {
          date: taskDate,
          productKey: CURRENT_PRODUCT_KEY,
          completion: 0,
          completedCount: 0,
          totalCount: 0,
          estimatedMinutes: 0,
          tasks: [],
        },
      })
    }
    const query = date ? `?date=${encodeURIComponent(date)}` : ''
    return d.request<d.DailyTaskList>(`/api/product/daily-tasks${query}`)
  },

  updateDailyTaskProgress(
    taskId: string,
    payload: {
      event: d.DailyTaskEvent
      currentStep?: number
      totalSteps?: number
      draft?: Record<string, unknown>
    },
  ): Promise<d.ApiRes<d.DailyLearningTask>> {
    return d.request<d.DailyLearningTask>(`/api/product/daily-tasks/${taskId}/progress`, {
      method: 'POST',
      data: payload,
    })
  },
}
