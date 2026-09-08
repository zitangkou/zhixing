import * as m from './_core'

export const mockExam = {
  // ===== 真题/题库（mock） =====
  async listExamPapers(): Promise<import('@/types').ApiRes<import('@/types').ExamPaper[]>> {
    await m.delay(200)
    return m.ok([
      {
        id: 'paper-mock-1',
        title: '2024 国考行测地市级',
        examType: 'real',
        subject: '行测',
        year: 2024,
        region: '国考',
        level: '地市级',
        totalCount: 135,
        timeLimitMin: 120,
        tags: ['行测', '真题'],
        isPublished: true,
        isFree: true,
        sortOrder: 0,
        description: '2024年国家公务员考试行测地市级真题',
        createdAt: new Date().toISOString(),
      },
    ])
  },
  async getExamPaperDetail(
    paperId: string,
  ): Promise<import('@/types').ApiRes<import('@/types').ExamPaperDetail>> {
    await m.delay(200)
    return m.ok({
      id: paperId,
      title: 'mock 试卷',
      examType: 'real',
      subject: '行测',
      year: 2024,
      region: '国考',
      level: '',
      totalCount: 2,
      timeLimitMin: 60,
      tags: [],
      isPublished: true,
      isFree: true,
      description: '',
      sections: [
        {
          section: '常识判断',
          questions: [
            {
              id: 'eq1',
              paperId,
              section: '常识判断',
              sectionIndex: 1,
              sortOrder: 1,
              type: 'single',
              material: '',
              stem: '首都？',
              options: ['北京', '上海', '广州', '深圳'],
              correctAnswer: '北京',
              analysis: '',
              difficulty: 3,
              knowledgeTags: [],
              isActive: true,
            },
          ],
        },
      ],
    })
  },
  async startExam(
    paperId: string,
  ): Promise<import('@/types').ApiRes<import('@/types').ExamStartResult>> {
    await m.delay(200)
    return m.ok({
      attemptId: `ea-mock-${Date.now()}`,
      paperId,
      paperTitle: 'mock 试卷',
      timeLimitMin: 60,
      totalCount: 1,
      startedAt: new Date().toISOString(),
      questions: [
        {
          id: 'eq1',
          section: '常识判断',
          sortOrder: 1,
          type: 'single',
          material: '',
          stem: '首都？',
          options: ['北京', '上海', '广州', '深圳'],
          myAnswer: '',
          marked: false,
          timeUsedSec: 0,
        },
      ],
    })
  },
  async submitExamAnswer(
    _attemptId: string,
    _data: { questionId: string; answer: string | string[] },
  ): Promise<import('@/types').ApiRes<{ ok: boolean }>> {
    await m.delay(50)
    return m.ok({ ok: true })
  },
  async submitExam(
    attemptId: string,
  ): Promise<import('@/types').ApiRes<import('@/types').ExamAttemptDetail>> {
    await m.delay(200)
    return m.ok({
      id: attemptId,
      paperId: 'paper-mock-1',
      paperTitle: 'mock 试卷',
      startedAt: new Date().toISOString(),
      finishedAt: new Date().toISOString(),
      timeUsedSec: 300,
      totalCount: 1,
      answeredCount: 1,
      correctCount: 1,
      score: 1,
      isFinished: true,
      answers: [
        {
          questionId: 'eq1',
          section: '常识判断',
          sortOrder: 1,
          stem: '首都？',
          options: ['北京', '上海', '广州', '深圳'],
          correctAnswer: '北京',
          analysis: '',
          userAnswer: '北京',
          isCorrect: true,
          answered: true,
          timeUsedSec: 30,
          marked: false,
        },
      ],
      sectionStats: [{ section: '常识判断', total: 1, correct: 1, answered: 1, accuracy: 100 }],
    })
  },
  async listExamAttempts(
    _paperId?: string,
  ): Promise<import('@/types').ApiRes<import('@/types').ExamAttempt[]>> {
    await m.delay(200)
    return m.ok([])
  },
  async getExamAttemptDetail(
    attemptId: string,
  ): Promise<import('@/types').ApiRes<import('@/types').ExamAttemptDetail>> {
    return this.submitExam(attemptId)
  },
}
