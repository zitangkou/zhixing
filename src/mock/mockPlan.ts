import * as m from './_core'

export const mockPlan = {
  // ===== 每日学习清单（mock） =====
  async getTodayPlan(): Promise<import('@/types').ApiRes<import('@/types').DayPlan>> {
    await m.delay(200)
    return this.getDayPlan(m.formatDate())
  },
  async getDayPlan(date: string): Promise<import('@/types').ApiRes<import('@/types').DayPlan>> {
    await m.delay(200)
    const isWeekend = [0, 6].includes(new Date(date).getDay())
    if (!m.mockState.planTasksByDate[date]) {
      const tmpl = isWeekend
        ? [
            {
              timeSlot: '07:30-09:00',
              subject: '行测',
              content: '行测套题模拟（第1段）',
              expectedMinutes: 90,
            },
            {
              timeSlot: '09:30-11:00',
              subject: '行测',
              content: '行测套题模拟（第2段）',
              expectedMinutes: 90,
            },
            {
              timeSlot: '11:00-12:00',
              subject: '行测',
              content: '套题对答案 + 错题录入',
              expectedMinutes: 60,
            },
            {
              timeSlot: '13:30-15:00',
              subject: '申论',
              content: '申论大作文 / 小题练笔',
              expectedMinutes: 90,
            },
            {
              timeSlot: '15:00-17:00',
              subject: '申论',
              content: '申论范文精读 + 素材整理',
              expectedMinutes: 120,
            },
            {
              timeSlot: '17:00-18:00',
              subject: '时政',
              content: '时政·人民日报精读 + 复述录音',
              expectedMinutes: 60,
            },
            {
              timeSlot: '19:00-21:00',
              subject: '行测',
              content: '弱项专项 + 错题复盘',
              expectedMinutes: 120,
            },
            {
              timeSlot: '21:00-22:00',
              subject: '复盘',
              content: '当日/本周复盘 + 下周计划',
              expectedMinutes: 60,
            },
          ]
        : [
            {
              timeSlot: '06:45-07:45',
              subject: '行测',
              content: '晨间行测刷题',
              expectedMinutes: 35,
            },
            {
              timeSlot: '08:00-08:30',
              subject: '时政',
              content: '早饭+散步：时政新闻跟读 20min',
              expectedMinutes: 20,
            },
            {
              timeSlot: '12:00-12:30',
              subject: '时政',
              content: '时政素材阅读',
              expectedMinutes: 30,
            },
            { timeSlot: '12:30-13:00', subject: '休息', content: '午休', expectedMinutes: 30 },
            {
              timeSlot: '17:30-18:00',
              subject: '时政',
              content: '晚饭+散步：时政新闻跟读 20min',
              expectedMinutes: 20,
            },
            { timeSlot: '18:00-19:00', subject: '申论', content: '申论专项', expectedMinutes: 60 },
            {
              timeSlot: '19:00-20:00',
              subject: '行测',
              content: '行测错题复盘',
              expectedMinutes: 60,
            },
            {
              timeSlot: '20:00-21:00',
              subject: '行测',
              content: '行测新题刷题',
              expectedMinutes: 60,
            },
            {
              timeSlot: '21:00-21:30',
              subject: '申论',
              content: '申论规范词口述练习',
              expectedMinutes: 30,
            },
            {
              timeSlot: '21:30-22:00',
              subject: '复盘',
              content: '当日复盘 + 明日计划',
              expectedMinutes: 30,
            },
          ]
      m.mockState.planTasksByDate[date] = tmpl.map((t, i) => ({
        id: `pt-${date}-${i}`,
        planDate: date,
        timeSlot: t.timeSlot,
        subject: t.subject,
        content: t.content,
        priority: 3,
        expectedMinutes: t.expectedMinutes,
        actualMinutes: 0,
        status: 'pending' as const,
        sortOrder: i,
        note: '',
      }))
    }
    const tasks = m.mockState.planTasksByDate[date]
    const doneCount = tasks.filter((t) => t.status === 'done').length
    const totalCount = tasks.length
    const completion = totalCount ? Math.round((doneCount / totalCount) * 100) : 0
    const expectedMinutes = tasks.reduce((s, t) => s + t.expectedMinutes, 0)
    const actualMinutes = tasks.reduce((s, t) => s + (t.actualMinutes || 0), 0)
    const review = m.mockState.planReviewsByDate[date] || null
    return m.ok({
      date,
      isWeekend,
      tasks,
      completion,
      doneCount,
      totalCount,
      expectedMinutes,
      actualMinutes,
      review,
    })
  },
  async getWeekPlan(): Promise<import('@/types').ApiRes<import('@/types').DayPlan[]>> {
    await m.delay(200)
    const today = new Date()
    const out: import('@/types').DayPlan[] = []
    for (let i = 6; i >= 0; i--) {
      const d = new Date(today)
      d.setDate(d.getDate() - i)
      const r = await this.getDayPlan(d.toISOString().slice(0, 10))
      out.push(r.data)
    }
    return m.ok(out)
  },
  async updatePlanTask(
    taskId: string,
    data: { status?: string; actualMinutes?: number; note?: string },
  ): Promise<import('@/types').ApiRes<import('@/types').PlanTask>> {
    await m.delay(100)
    const dateFromId = /^pt-(\d{4}-\d{2}-\d{2})-/.exec(taskId)?.[1]
    if (dateFromId && !m.mockState.planTasksByDate[dateFromId]) {
      await this.getDayPlan(dateFromId)
    }
    for (const date of Object.keys(m.mockState.planTasksByDate)) {
      const tasks = m.mockState.planTasksByDate[date]
      const idx = tasks.findIndex((t) => t.id === taskId)
      if (idx < 0) continue
      const cur = tasks[idx]
      const next: import('@/types').PlanTask = {
        ...cur,
        status:
          data.status !== undefined ? (data.status as 'pending' | 'done' | 'skipped') : cur.status,
        actualMinutes: data.actualMinutes !== undefined ? data.actualMinutes : cur.actualMinutes,
        note: data.note !== undefined ? data.note : cur.note,
      }
      tasks[idx] = next
      return m.ok(next)
    }
    return { code: 404, data: null as unknown as import('@/types').PlanTask, message: '任务不存在' }
  },
  async addPlanTask(data: {
    planDate: string
    content: string
    timeSlot?: string
    subject?: string
    expectedMinutes?: number
  }): Promise<import('@/types').ApiRes<import('@/types').PlanTask>> {
    await m.delay(100)
    await this.getDayPlan(data.planDate)
    const tasks = m.mockState.planTasksByDate[data.planDate]
    const task: import('@/types').PlanTask = {
      id: `pt-${Date.now()}`,
      planDate: data.planDate,
      timeSlot: data.timeSlot || '',
      subject: data.subject || '',
      content: data.content,
      priority: 3,
      expectedMinutes: data.expectedMinutes || 0,
      actualMinutes: 0,
      status: 'pending',
      sortOrder: tasks.length,
      note: '',
    }
    tasks.push(task)
    return m.ok(task)
  },
  async deletePlanTask(taskId: string): Promise<import('@/types').ApiRes<{ ok: boolean }>> {
    await m.delay(100)
    for (const date of Object.keys(m.mockState.planTasksByDate)) {
      const tasks = m.mockState.planTasksByDate[date]
      const idx = tasks.findIndex((t) => t.id === taskId)
      if (idx >= 0) {
        tasks.splice(idx, 1)
        break
      }
    }
    return m.ok({ ok: true })
  },
  async upsertReview(
    data: Partial<import('@/types').DailyReview> & { reviewDate: string },
  ): Promise<import('@/types').ApiRes<import('@/types').DailyReview>> {
    await m.delay(100)
    const reviewDate = data.reviewDate || m.formatDate()
    const prev = m.mockState.planReviewsByDate[reviewDate]
    const review: import('@/types').DailyReview = {
      reviewDate,
      completion: data.completion ?? prev?.completion ?? 0,
      totalMinutes: data.totalMinutes ?? prev?.totalMinutes ?? 0,
      weakPoint: data.weakPoint ?? prev?.weakPoint ?? '',
      tomorrowFocus: data.tomorrowFocus ?? prev?.tomorrowFocus ?? '',
      mood: (data.mood ?? prev?.mood ?? '') as import('@/types').DailyReview['mood'],
      note: data.note ?? prev?.note ?? '',
    }
    m.mockState.planReviewsByDate[reviewDate] = review
    return m.ok(review)
  },
}
