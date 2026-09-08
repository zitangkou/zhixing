import * as d from '../_shared'
import { CURRENT_PRODUCT_KEY } from '@/constants/product'

let mockDailyTask: d.DailyLearningTask | null = null

async function getMockDailyTasks(date?: string): Promise<d.ApiRes<d.DailyTaskList>> {
  const taskDate = date || new Date().toISOString().slice(0, 10)
  if (CURRENT_PRODUCT_KEY === 'general') {
    return {
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
    }
  }
  if (CURRENT_PRODUCT_KEY === 'shenlun') {
    const articleRes = await d.mockService.listRmrbArticles()
    const article = articleRes.data?.[0]
    if (article && (!mockDailyTask || mockDailyTask.taskDate !== taskDate)) {
      mockDailyTask = {
        id: 'dlt-mock-shenlun',
        productKey: 'shenlun',
        taskDate,
        taskType: 'shenlun_article_training',
        title: article.title,
        description: article.summary || '精读一篇时评，完成三刀拆解与表达沉淀',
        contentType: 'rmrb_article',
        contentId: article.id,
        estimatedMinutes: 15,
        totalSteps: 4,
        sortOrder: 0,
        metadata: {
          source: article.source,
          tags: article.tags,
          steps: [
            { key: 'read', title: '精读定位', description: '读懂主题、对象与核心问题' },
            { key: 'analyze', title: '三刀拆解', description: '拆骨架、抓规范表达、学句式' },
            { key: 'answer', title: '小题作答', description: '围绕材料完成一次短作答' },
            { key: 'deposit', title: '表达沉淀', description: '留下一个可迁移表达' },
          ],
          question: {
            type: '概括练习',
            prompt: '请用不超过120字，概括文章关注的核心问题与主要解决思路。',
            maxLength: 120,
            checks: ['对象和主题明确', '核心问题或成效清楚', '做法、原因有材料依据'],
          },
          depositPrompt: '写下今天最值得迁移到申论作答中的一个规范表达。',
        },
        progress: { state: 'not_started', currentStep: 0, totalSteps: 4, draft: {} },
      }
    }
  } else {
    const articleRes = await d.mockService.getDailyArticles()
    const article = articleRes.data?.[0]
    const questionRes = article ? await d.mockService.getQuestions(article.id) : null
    if (article && (!mockDailyTask || mockDailyTask.taskDate !== taskDate)) {
      const questionCount = questionRes?.data?.length || 0
      mockDailyTask = {
        id: 'dlt-mock-theory',
        productKey: 'theory',
        taskDate,
        taskType: 'theory_daily_pack',
        title: article.title,
        description: article.summary || '理解一个理论主题，用原文依据辨清易混表述',
        contentType: 'article',
        contentId: article.id,
        estimatedMinutes: 15,
        totalSteps: 4,
        sortOrder: 0,
        metadata: {
          source: article.source,
          focuses: article.tags.slice(0, 3),
          questionCount,
          evidenceCount: questionCount,
          steps: [
            { key: 'orient', title: '读前定向', description: '先看主体、行动与限定条件' },
            { key: 'read', title: '原文精读', description: '理解规范表述和知识位置' },
            { key: 'quiz', title: '证据刷题', description: '每道题都回到原文依据' },
            { key: 'review', title: '错因回收', description: '辨清偷换、扩大与程度变化' },
          ],
        },
        progress: { state: 'not_started', currentStep: 0, totalSteps: 4, draft: {} },
      }
    }
  }
  const tasks = mockDailyTask ? [mockDailyTask] : []
  const completedCount = tasks.filter((task) => task.progress.state === 'completed').length
  return {
    code: 0,
    message: 'ok',
    data: {
      date: taskDate,
      productKey: CURRENT_PRODUCT_KEY,
      completion: completedCount ? 100 : 0,
      completedCount,
      totalCount: tasks.length,
      estimatedMinutes: tasks.reduce((sum, task) => sum + task.estimatedMinutes, 0),
      tasks,
    },
  }
}

export const apiProduct = {
  getDailyTasks(date?: string): Promise<d.ApiRes<d.DailyTaskList>> {
    if (d.isMock) return getMockDailyTasks(date)
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
    if (d.isMock && mockDailyTask?.id === taskId) {
      const stateByEvent: Record<d.DailyTaskEvent, d.DailyTaskState> = {
        start: 'in_progress',
        save: 'in_progress',
        submit: 'submitted',
        review: 'reviewed',
        complete: 'completed',
      }
      mockDailyTask = {
        ...mockDailyTask,
        progress: {
          ...mockDailyTask.progress,
          state: stateByEvent[payload.event],
          currentStep: payload.currentStep ?? mockDailyTask.progress.currentStep,
          totalSteps: payload.totalSteps ?? mockDailyTask.progress.totalSteps,
          draft: payload.draft ?? mockDailyTask.progress.draft,
          updatedAt: new Date().toISOString(),
        },
      }
      return Promise.resolve({ code: 0, data: mockDailyTask, message: 'ok' })
    }
    return d.request<d.DailyLearningTask>(`/api/product/daily-tasks/${taskId}/progress`, {
      method: 'POST',
      data: payload,
    })
  },
}
