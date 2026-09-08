import * as m from './_core'

export const mockAuth = {
  async register(
    username: string,
    password: string,
    passwordConfirm?: string,
  ): Promise<import('@/types').ApiRes<import('@/api').AuthResult>> {
    await m.delay()
    if (password.length < 6) {
      return {
        code: 400,
        data: null as unknown as import('@/api').AuthResult,
        message: '密码至少 6 位',
      }
    }
    if (passwordConfirm && password !== passwordConfirm) {
      return {
        code: 400,
        data: null as unknown as import('@/api').AuthResult,
        message: '两次输入的密码不一致',
      }
    }
    m.mockState.userInfo = {
      id: `u-${username}`,
      username,
      nickname: username,
      avatar: '',
      email: '',
      phone: '',
      isMember: false,
    }
    const user = await this.getUserMe()
    return m.ok({
      access_token: 'mock-token',
      token_type: 'bearer',
      user: user.data,
    })
  },

  async login(
    username: string,
    _password: string,
  ): Promise<import('@/types').ApiRes<import('@/api').AuthResult>> {
    await m.delay()
    m.mockState.userInfo = {
      id: `u-${username}`,
      username,
      nickname: username,
      avatar: '',
      email: '',
      phone: '',
      isMember: false,
    }
    const user = await this.getUserMe()
    return m.ok({
      access_token: 'mock-token',
      token_type: 'bearer',
      user: user.data,
    })
  },

  async getUserMe(): Promise<import('@/types').ApiRes<import('@/api').UserMeData>> {
    await m.delay()
    const today = m.formatDate()
    return m.ok({
      id: m.mockState.userInfo.id,
      username: m.mockState.userInfo.username,
      nickname: m.mockState.userInfo.nickname,
      avatar: m.mockState.userInfo.avatar,
      email: m.mockState.userInfo.email || '',
      phone: m.mockState.userInfo.phone || '',
      isMember: m.mockState.userInfo.isMember,
      points: m.mockState.points,
      hasSignedToday: !!m.mockState.signStatus[today],
      signDates: Object.keys(m.mockState.signStatus).filter((k) => m.mockState.signStatus[k]),
    })
  },

  async updateProfile(data: {
    nickname?: string
    email?: string
    phone?: string
  }): Promise<import('@/types').ApiRes<import('@/api').UserMeData>> {
    await m.delay()
    if (data.nickname !== undefined) {
      const name = data.nickname.trim()
      if (!name)
        return {
          code: 400,
          data: null as unknown as import('@/api').UserMeData,
          message: '昵称不能为空',
        }
      m.mockState.userInfo.nickname = name
    }
    if (data.email !== undefined) m.mockState.userInfo.email = data.email.trim()
    if (data.phone !== undefined) m.mockState.userInfo.phone = data.phone.trim()
    return this.getUserMe()
  },

  async changePassword(data: {
    oldPassword: string
    newPassword: string
    newPasswordConfirm: string
  }): Promise<import('@/types').ApiRes<{ ok: boolean }>> {
    await m.delay()
    if (data.newPassword.length < 6) {
      return { code: 400, data: null as unknown as { ok: boolean }, message: '密码至少 6 位' }
    }
    if (data.newPassword !== data.newPasswordConfirm) {
      return {
        code: 400,
        data: null as unknown as { ok: boolean },
        message: '两次输入的新密码不一致',
      }
    }
    if (!data.oldPassword) {
      return { code: 400, data: null as unknown as { ok: boolean }, message: '请输入原密码' }
    }
    return m.ok({ ok: true })
  },

  async uploadAvatar(
    filePath: string,
  ): Promise<import('@/types').ApiRes<import('@/api').UserMeData>> {
    await m.delay()
    m.mockState.userInfo.avatar = filePath
    return this.getUserMe()
  },

  async getDailyArticles(): Promise<import('@/types').ApiRes<import('@/types').Article[]>> {
    await m.delay()
    const today = m.formatDate()
    const sorted = [...m.mockArticles].sort(
      (a, b) => Number(Boolean(b.isFeatured)) - Number(Boolean(a.isFeatured)),
    )
    return m.ok(sorted.map((a) => ({ ...a, publishDate: a.isFeatured ? a.publishDate : today })))
  },

  async getRecommendedArticles(
    offset = 0,
    limit = 5,
  ): Promise<import('@/types').ApiRes<import('@/types').ArticleListPage>> {
    await m.delay()
    const pool = [...m.mockArticles]
      .filter((a) => !a.isFeatured)
      .sort((a, b) => {
        const byDate = b.publishDate.localeCompare(a.publishDate)
        if (byDate) return byDate
        return String(b.id).localeCompare(String(a.id))
      })
    const items = pool.slice(offset, offset + limit)
    return m.ok({
      items,
      total: pool.length,
      hasMore: offset + items.length < pool.length,
    })
  },

  async getArticleDetail(
    id: string,
  ): Promise<import('@/types').ApiRes<import('@/types').Article | null>> {
    await m.delay()
    const article = m.mockArticles.find((a) => a.id === id)
    return m.ok(article || null, article ? 'success' : '文章不存在')
  },

  async getQuestions(
    articleId: string,
  ): Promise<import('@/types').ApiRes<import('@/types').Question[]>> {
    await m.delay()
    const questions = m.questionBank.get(articleId) || []
    return m.ok(questions)
  },

  async getQuizByMode(
    mode: string,
    count = 10,
  ): Promise<import('@/types').ApiRes<import('@/types').Question[]>> {
    await m.delay()
    const all: import('@/types').Question[] = []
    m.questionBank.forEach((qs) => all.push(...qs))
    if (!all.length) return m.ok([])
    if (mode === 'timeline') {
      const sortedArticles = [...m.mockArticles].sort((a, b) =>
        b.publishDate.localeCompare(a.publishDate),
      )
      const recentIds = new Set(sortedArticles.slice(0, 3).map((a) => a.id))
      const filtered = all.filter((q) => recentIds.has(q.articleId))
      const pool = filtered.length ? filtered : all
      return m.ok(m.shuffle(pool).slice(0, count))
    }
    if (mode === 'key') {
      const keyIds = new Set(
        m.mockArticles.filter((a) => (a.importance || 0) >= 4 || a.isFeatured).map((a) => a.id),
      )
      const filtered = all.filter((q) => keyIds.has(q.articleId))
      const pool = filtered.length ? filtered : all
      return m.ok(m.shuffle(pool).slice(0, count))
    }
    return m.ok(m.shuffle(all).slice(0, count))
  },

  async submitAnswer(
    questionId: string,
    answer: string | string[],
  ): Promise<import('@/types').ApiRes<import('@/types').AnswerResult>> {
    await m.delay()
    let target: import('@/types').Question | undefined
    for (const qs of m.questionBank.values()) {
      target = qs.find((q) => q.id === questionId)
      if (target) break
    }
    if (!target) {
      return {
        code: 404,
        data: null as unknown as import('@/types').AnswerResult,
        message: '题目不存在',
      }
    }

    const correct = m.checkAnswer(target, answer)
    let pointsEarned = 0
    if (correct) {
      pointsEarned = m.POINTS_RULES.CORRECT_ANSWER
      m.addPointsLog(pointsEarned, '答题', `答对：${target.stem.slice(0, 20)}...`)
    } else {
      const existing = m.mockState.wrongQuestions.get(questionId)
      m.mockState.wrongQuestions.set(questionId, {
        question: target,
        wrongCount: (existing?.wrongCount || 0) + 1,
        lastWrongAt: new Date().toISOString(),
        userAnswer: answer,
      })
    }

    return m.ok({
      correct,
      analysis: target.analysis,
      correctAnswer: target.correctAnswer,
      pointsEarned,
    })
  },

  async getReviewTasks(
    records: import('@/types').StudyRecord[],
  ): Promise<import('@/types').ApiRes<import('@/types').ReviewTask[]>> {
    await m.delay()
    const merged = records.length ? records : m.mockState.studyRecords
    const tasks = m.generateReviewTasks(merged, m.mockArticles)
    return m.ok(tasks)
  },

  async getWrongQuestions(): Promise<
    import('@/types').ApiRes<import('@/types').WrongQuestionRecord[]>
  > {
    await m.delay()
    const list = Array.from(m.mockState.wrongQuestions.values()).map((record) => {
      const article = m.mockArticles.find((a) => a.id === record.question.articleId)
      return {
        question: record.question,
        wrongCount: record.wrongCount,
        lastWrongAt: record.lastWrongAt,
        userAnswer: record.userAnswer,
        articleTitle: article?.title || '未知文章',
        tag: article?.tags[0] || '综合',
      }
    })
    return m.ok(list)
  },

  async redoWrongQuestion(
    questionId: string,
    answer: string | string[],
  ): Promise<import('@/types').ApiRes<import('@/types').AnswerResult>> {
    await m.delay()
    const item = m.mockState.wrongQuestions.get(questionId)
    if (!item) {
      return {
        code: 404,
        data: null as unknown as import('@/types').AnswerResult,
        message: '题目不存在',
      }
    }
    const correct = m.checkAnswer(item.question, answer)
    let pointsEarned = 0
    if (correct) {
      m.mockState.wrongQuestions.delete(questionId)
      pointsEarned = m.POINTS_RULES.WRONG_REVIEW
      m.addPointsLog(pointsEarned, '复习', '错题复习答对')
    }
    return m.ok({
      correct,
      analysis: item.question.analysis,
      correctAnswer: item.question.correctAnswer,
      pointsEarned,
    })
  },

  async removeWrongQuestion(questionId: string): Promise<import('@/types').ApiRes<null>> {
    await m.delay()
    if (!m.mockState.wrongQuestions.has(questionId)) {
      return { code: 404, data: null, message: '错题记录不存在' }
    }
    m.mockState.wrongQuestions.delete(questionId)
    return m.ok(null)
  },

  async getStudyRecords(): Promise<import('@/types').ApiRes<import('@/types').StudyRecord[]>> {
    await m.delay()
    return m.ok(m.mockState.studyRecords)
  },

  async getSectionReads(): Promise<import('@/types').ApiRes<Record<string, string[]>>> {
    await m.delay()
    return m.ok(m.mockState.sectionReadMap)
  },

  async markSectionRead(
    articleId: string,
    sectionId: string,
  ): Promise<import('@/types').ApiRes<null>> {
    await m.delay()
    const list = m.mockState.sectionReadMap[articleId] || []
    if (!list.includes(sectionId)) {
      m.mockState.sectionReadMap[articleId] = [...list, sectionId]
    }
    return m.ok(null)
  },

  async signIn(): Promise<import('@/types').ApiRes<{ points: number; streak: number }>> {
    await m.delay()
    const today = m.formatDate()
    if (m.mockState.signStatus[today]) {
      return { code: 400, data: { points: 0, streak: 0 }, message: '今日已签到' }
    }
    m.mockState.signStatus[today] = true
    const streak = m.calcSignStreak(m.mockState.signStatus, today)
    let points = m.POINTS_RULES.SIGN_BASE
    if (streak >= 7 && streak % 7 === 0) {
      points += m.POINTS_RULES.SIGN_STREAK_BONUS
    }
    m.addPointsLog(points, '签到', `第${streak}天连续签到`)
    return m.ok({ points, streak })
  },

  async getPointsLog(): Promise<import('@/types').ApiRes<import('@/types').PointsLog[]>> {
    await m.delay()
    return m.ok(m.mockState.pointsLogs)
  },

  async getPoints(): Promise<import('@/types').ApiRes<number>> {
    await m.delay()
    return m.ok(m.mockState.points)
  },

  async getRankList(
    type: import('@/constants').RankType,
  ): Promise<import('@/types').ApiRes<import('@/types').RankItem[]>> {
    await m.delay()
    const factor = type === 'daily' ? 0.1 : type === 'weekly' ? 0.3 : type === 'monthly' ? 0.6 : 1
    const list = m.mockRankUsers
      .map((u, i) => ({
        rank: i + 1,
        ...u,
        score: u.userId === 'self' ? m.mockState.points : Math.round(u.score * factor),
        isSelf: u.userId === 'self',
      }))
      .sort((a, b) => b.score - a.score)
      .map((item, i) => ({ ...item, rank: i + 1 }))

    return m.ok(list)
  },

  async completeQuiz(data: {
    articleId?: string
    mode: string
    total: number
    correct: number
  }): Promise<import('@/types').ApiRes<import('@/types').QuizCompleteResult>> {
    await m.delay()
    const accuracy = data.total > 0 ? Math.round((data.correct / data.total) * 100) : 0
    m.mockState.quizAttempts.push({
      userId: 'self',
      articleId: data.articleId,
      mode: data.mode,
      total: data.total,
      correct: data.correct,
      accuracy,
    })
    const same = m.mockState.quizAttempts.filter(
      (a) => a.articleId === data.articleId && a.mode === data.mode,
    )
    const bestByUser = new Map<string, number>()
    same.forEach((a) => {
      const prev = bestByUser.get(a.userId) ?? 0
      if (a.accuracy > prev) bestByUser.set(a.userId, a.accuracy)
    })
    const sorted = [...bestByUser.entries()].sort((a, b) => b[1] - a[1])
    const rank = sorted.findIndex(([uid]) => uid === 'self') + 1 || sorted.length + 1
    const prevBest = Math.max(0, ...same.filter((a) => a.userId === 'self').map((a) => a.accuracy))
    return m.ok({
      accuracy,
      rank: rank || 1,
      totalParticipants: bestByUser.size || 1,
      bestAccuracy: prevBest,
    })
  },

  async getQuizRank(
    articleId?: string,
    mode = 'article',
  ): Promise<import('@/types').ApiRes<import('@/types').QuizRankItem[]>> {
    await m.delay()
    const same = m.mockState.quizAttempts.filter(
      (a) => a.articleId === articleId && a.mode === mode,
    )
    const bestByUser = new Map<string, (typeof same)[0]>()
    same.forEach((a) => {
      const prev = bestByUser.get(a.userId)
      if (!prev || a.accuracy > prev.accuracy) bestByUser.set(a.userId, a)
    })
    const list = [...bestByUser.values()]
      .sort((a, b) => b.accuracy - a.accuracy || b.correct - a.correct)
      .slice(0, 20)
      .map((a, i) => ({
        rank: i + 1,
        userId: a.userId,
        nickname: a.userId === 'self' ? m.mockState.userInfo.nickname : `学员${i + 1}`,
        avatar: '',
        accuracy: a.accuracy,
        correctCount: a.correct,
        totalCount: a.total,
        isSelf: a.userId === 'self',
      }))
    return m.ok(list)
  },

  async markArticleRead(articleId: string): Promise<import('@/types').ApiRes<{ points: number }>> {
    await m.delay()
    if (m.mockState.readArticles.has(articleId)) {
      return m.ok({ points: 0 })
    }
    m.mockState.readArticles.add(articleId)
    const existing = m.mockState.studyRecords.find((r) => r.articleId === articleId)
    if (!existing) {
      m.mockState.studyRecords.push({
        articleId,
        studyDate: m.formatDate(),
        reviewCount: 0,
        mastered: false,
      })
    }
    m.addPointsLog(m.POINTS_RULES.READ_ARTICLE, '阅读', '完成文章阅读')
    return m.ok({ points: m.POINTS_RULES.READ_ARTICLE })
  },

  async completeReview(articleId: string): Promise<import('@/types').ApiRes<void>> {
    await m.delay()
    const record = m.mockState.studyRecords.find((r) => r.articleId === articleId)
    if (record) {
      record.reviewCount++
      record.lastReviewDate = m.formatDate()
      if (record.reviewCount >= 6) record.mastered = true
    }
    return m.ok(undefined as void)
  },

  async submitFeedback(_content: string): Promise<import('@/types').ApiRes<{ adopted: boolean }>> {
    await m.delay(500)
    const adopted = Math.random() > 0.5
    if (adopted) {
      m.addPointsLog(m.POINTS_RULES.FEEDBACK_ADOPTED, '反馈', '纠错反馈被采纳')
    }
    return m.ok({ adopted })
  },
}
