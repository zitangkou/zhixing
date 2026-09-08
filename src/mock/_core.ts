import type { ApiRes, PointsLog, Question, StudyRecord, UserInfo } from '@/types'
import { mockArticles, mockRankUsers } from '@/mock/articles'
import { buildQuestionBank, checkAnswer } from '@/utils/questionGenerator'
import { calcSignStreak, formatDate, generateReviewTasks } from '@/utils/memoryCurve'
import { POINTS_RULES } from '@/constants'

export {
  mockArticles,
  mockRankUsers,
  checkAnswer,
  calcSignStreak,
  formatDate,
  generateReviewTasks,
  POINTS_RULES,
  buildQuestionBank,
}

export const questionBank = buildQuestionBank(mockArticles)

export const mockCorpusItems: import('@/types').CorpusItem[] = []

export function shuffle<T>(arr: T[]): T[] {
  const copy = [...arr]
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

/** 模拟延迟 */
export const delay = (ms = 300) => new Promise((r) => setTimeout(r, ms))

export const mockZiliaoMaterial =
  '2023年，某市新能源汽车产量为 48 万辆，同比增长 25%；其中纯电动汽车产量 36 万辆，同比增长 20%。同年该市汽车总产量 120 万辆，同比增长 10%。'

export const mockZiliao = {
  todaySets: 0,
  todayCorrect: 0,
  todayTotal: 0,
  formulas: [
    {
      id: 'zf_mock_1',
      code: 'F001',
      name: '增长率',
      category: '增长',
      definition: '反映现期相对基期的增长快慢。',
      latex: 'r=\\dfrac{A_{1}-A_{0}}{A_{0}}',
      formulaPlain: '增长率 = (现期 − 基期) / 基期',
      scenarios: '同比增长多少、增幅是多少',
      pitfalls: '分母是基期不是现期',
      relatedTypeCodes: ['T001'],
      relatedTrickCodes: ['K001'],
      keywords: ['增长率'],
      examFreq: 5,
      sortOrder: 1,
      isPublished: true,
    },
  ] as import('@/types').ZiliaoFormula[],
  types: [
    {
      id: 'zt_mock_1',
      code: 'T001',
      name: '增长率计算',
      category: '增长',
      description: '直接求同比/环比增长率',
      ability: '定位数据 + 公式计算',
      difficulty: 2,
      examFreq: 5,
      formulaCodes: ['F001'],
      trickCodes: ['K001'],
      keywords: ['增长率'],
      sortOrder: 1,
      isPublished: true,
    },
  ] as import('@/types').ZiliaoQuestionType[],
  tricks: [
    {
      id: 'zk_mock_1',
      code: 'K001',
      name: '首数法',
      category: '直除',
      principle: '只看商的前几位数字，快速锁定选项。',
      whenToUse: '选项首位不同',
      whenNot: '选项非常接近',
      errorNote: '一般可保证首位正确',
      formulaCodes: ['F001'],
      example: '150÷998 ≈ 15%',
      sortOrder: 1,
      isPublished: true,
    },
  ] as import('@/types').ZiliaoTrick[],
  drill: {
    setId: 'ziliao_sample_paper:mockmat',
    paperId: 'ziliao_sample_paper',
    paperTitle: '资料分析专项样例（入门）',
    material: mockZiliaoMaterial,
    questions: [
      {
        id: 'eq_mock_1',
        section: '资料分析',
        sortOrder: 1,
        type: 'single',
        material: mockZiliaoMaterial,
        stem: '2023年该市新能源汽车产量比上年增长了多少万辆？',
        options: ['8.4', '9.6', '12.0', '14.4'],
        difficulty: 2,
      },
      {
        id: 'eq_mock_2',
        section: '资料分析',
        sortOrder: 2,
        type: 'single',
        material: mockZiliaoMaterial,
        stem: '2023年纯电动汽车产量占新能源汽车产量的比重约为？',
        options: ['65%', '75%', '80%', '85%'],
        difficulty: 2,
      },
    ],
  } as import('@/types').ZiliaoDrillSetDetail,
  correctMap: { eq_mock_1: 'B', eq_mock_2: 'B' } as Record<string, string>,
  analysisMap: {
    eq_mock_1: '基期=48/1.25=38.4，增长量=9.6。选 B。',
    eq_mock_2: '36/48=75%。选 B。',
  } as Record<string, string>,
}

/** 内存态 Mock 存储 */
export const mockState = {
  points: 120,
  pointsLogs: [] as PointsLog[],
  signStatus: {} as Record<string, boolean>,
  readArticles: new Set<string>(),
  studyRecords: [] as StudyRecord[],
  sectionReadMap: {} as Record<string, string[]>,
  wrongQuestions: new Map<
    string,
    { question: Question; wrongCount: number; lastWrongAt: string; userAnswer?: string | string[] }
  >(),
  quizAttempts: [] as Array<{
    userId: string
    articleId?: string
    mode: string
    total: number
    correct: number
    accuracy: number
  }>,
  userInfo: {
    id: 'self',
    nickname: '知行学员',
    avatar: '',
    email: '',
    phone: '',
    isMember: false,
  } as UserInfo,
  events: null as import('@/types').EventImpression[] | null,
  countdown: null as import('@/types').ExamCountdown | null,
  manualWrongs: [] as import('@/types').ManualWrong[],
  planTasksByDate: {} as Record<string, import('@/types').PlanTask[]>,
  planReviewsByDate: {} as Record<string, import('@/types').DailyReview>,
}

export function ok<T>(data: T, message = 'success'): ApiRes<T> {
  return { code: 0, data, message }
}

export const mockRmrb = {
  mines: [] as import('@/types').ShenlunMineLog[],
  terms: [] as import('@/types').ShenlunNormTerm[],
  drills: [] as import('@/types').ShenlunDrillLog[],
}

export function addPointsLog(
  amount: number,
  source: string,
  description: string,
  type: 'income' | 'expense' = 'income',
) {
  mockState.points += type === 'income' ? amount : -amount
  mockState.pointsLogs.unshift({
    id: `log-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    amount,
    type,
    source,
    description,
    createdAt: new Date().toISOString(),
  })
}
