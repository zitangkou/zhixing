/** 资料分析速算：先构造方法适用条件，再用整数交叉乘积校验比较结论。 */
export type QuickMethod =
  'direct' | 'difference' | 'position' | 'split' | 'growth-amount' | 'growth-rate' | 'base'
export type QuickMode = QuickMethod | 'mixed'
export interface QuickMethodInfo {
  id: QuickMethod
  name: string
  scene: string
  path: string
  nodeTitle: string
  nodeParent?: string
}
export const QUICK_METHODS: QuickMethodInfo[] = [
  {
    id: 'direct',
    name: '分数性质',
    scene: '分子更大、分母更小，直接判定。',
    path: '资料分析 / 快速比较方法',
    nodeTitle: '快速比较方法',
  },
  {
    id: 'difference',
    name: '差分比较',
    scene: '分子分母同向变大且差值简单，比较差分数与原分数。',
    path: '资料分析 / 快速比较方法 / 差分比较',
    nodeTitle: '差分比较',
  },
  {
    id: 'position',
    name: '同位比较',
    scene: '分子和分母跨过同一倍数界线的方向相反。',
    path: '资料分析 / 快速比较方法 / 同位比较',
    nodeTitle: '同位比较',
  },
  {
    id: 'split',
    name: '分母拆分',
    scene: '两个正分数接近 1，转为“部分 / 剩余”后容易比较。',
    path: '资料分析 / 快速比较方法 / 分母拆分',
    nodeTitle: '分母拆分',
  },
  {
    id: 'growth-amount',
    name: '增长量 · n＋1',
    scene: '正增长率为 1/n，增长量＝现期量 / (n＋1)。',
    path: '资料分析 / 增长 / 增长量 / 快速计算方法',
    nodeTitle: '增长量',
    nodeParent: '增长',
  },
  {
    id: 'growth-rate',
    name: '增长率',
    scene: '已知现期量、基期量，先求差，再除以基期量。',
    path: '资料分析 / 增长 / 增长率',
    nodeTitle: '增长率',
    nodeParent: '增长',
  },
  {
    id: 'base',
    name: '基期量',
    scene: '现期量＝基期量×(1＋增长率)，逆推基期量。',
    path: '资料分析 / 增长 / 基期值',
    nodeTitle: '基期值',
    nodeParent: '增长',
  },
]
export interface QuickStep {
  text: string
  latex?: string
}
export interface QuickQuestion {
  id: string
  method: QuickMethod
  stem: string
  latex: string
  plain: string
  options: string[]
  answer: number
  steps: QuickStep[]
  pitfall: string
  /** 用于独立精确校验，不依赖选项和解析文本。 */
  check:
    | { kind: 'compare'; values: [number, number, number, number] }
    | { kind: 'number'; target: number; values: number[]; unit: string }
}
export type RandomSource = () => number
const integer = (rng: RandomSource, min: number, max: number) =>
  min + Math.floor(rng() * (max - min + 1))
function shuffle<T>(items: T[], rng: RandomSource): T[] {
  const result = [...items]
  for (let i = result.length - 1; i > 0; i--) {
    const j = integer(rng, 0, i)
    ;[result[i], result[j]] = [result[j], result[i]]
  }
  return result
}
const frac = (a: number, b: number) => `\\frac{${a}}{${b}}`
const format = (n: number) => Number(n.toFixed(2)).toString()
export function methodInfo(id: QuickMethod): QuickMethodInfo {
  return QUICK_METHODS.find((m) => m.id === id)!
}

function comparison(method: QuickMethod, rng: RandomSource): Omit<QuickQuestion, 'id'> {
  let a = 0,
    b = 0,
    c = 0,
    d = 0
  let steps: QuickStep[] = []
  let pitfall = ''
  if (method === 'direct') {
    c = integer(rng, 1500, 9500)
    d = integer(rng, 1500, 9500)
    a = c + integer(rng, 20, 200)
    b = d - integer(rng, 20, 200)
    steps = [{ text: `左边分子 ${a} 大于 ${c}，分母 ${b} 小于 ${d}，所以左边分数更大。` }]
    pitfall = '分子、分母都更大时，不能直接说分数更大。'
  } else if (method === 'difference') {
    const k = integer(rng, 3, 9),
      delta = integer(rng, 12, 40)
    d = integer(rng, 1100, 2400)
    c = k * d + integer(rng, 100, 400)
    const high = rng() > 0.5
    const da = (high ? k + 2 : k - 1) * delta
    b = d + delta
    a = c + da
    steps = [
      {
        text: `分子、分母都略大，作差得到简单的差分数。`,
        latex: `${frac(a - c, b - d)}=${format(da / delta)}`,
      },
      {
        text: `右边原分数处于 ${k} 与 ${k + 1} 之间；差分数${high ? '更大' : '更小'}，因此左边原分数${high ? '更大' : '更小'}。`,
        latex: `${k}<${frac(c, d)}<${k + 1}`,
      },
      {
        text: '左边是右边原分数与差分数按分母加权后的结果，大小落在二者之间。',
        latex: `${frac(a, b)}=\\frac{${c}+${a - c}}{${d}+${b - d}}`,
      },
    ]
    pitfall = '差分法要求分子、分母同向作差且差分母为正；“较小”指分子分母较小，不预设分数值较小。'
  } else if (method === 'position') {
    const k = integer(rng, 2, 4)
    c = integer(rng, 1200, 4000)
    d = integer(rng, 200, 600)
    a = k * c + integer(rng, 20, 100)
    b = k * d - integer(rng, 10, 60)
    steps = [
      {
        text: `分子超过 ${k} 倍，分母不足 ${k} 倍。`,
        latex: `${a}>${k}\\times${c},\\quad ${b}<${k}\\times${d}`,
      },
      {
        text: '左边分数比同时放大后的右边，分子更大且分母更小，因此左边更大。',
        latex: `${frac(a, b)}>${frac(k * c, k * d)}=${frac(c, d)}`,
      },
    ]
    pitfall = '分子、分母的倍数都在同一界线的同侧时，这一步不能判大小，应换方法。'
  } else {
    c = integer(rng, 6000, 9000)
    a = c + integer(rng, 400, 800)
    const leftRest = integer(rng, 150, 350),
      rightRest = leftRest + integer(rng, 30, 180)
    b = a + leftRest
    d = c + rightRest
    steps = [
      {
        text: '两个分数都接近 1，将“部分 / 整体”改比“部分 / 剩余”。正数条件下，这个变换保持大小关系。',
        latex: `${frac(a, b)}\\;\\longleftrightarrow\\;${frac(a, b - a)},\\quad ${frac(c, d)}\\;\\longleftrightarrow\\;${frac(c, d - c)}`,
      },
      {
        text: `改写后左边分子更大（${a}>${c}）、分母更小（${b - a}<${d - c}），所以原来的左边也更大。`,
      },
    ]
    pitfall = '这里要求 0＜分子＜分母，剩余量为正；不要只看原分数分子的大小。'
  }
  // 随机交换两边，避免同一方法总选“大于”。解析仍保留原来的数值方向。
  const swapped = rng() > 0.5
  if (swapped) {
    ;[a, b, c, d] = [c, d, a, b]
    steps = steps.map((step) => ({
      ...step,
      text: step.text.replace(/左边|右边/g, (word) => (word === '左边' ? '右边' : '左边')),
    }))
  }
  const options = shuffle(['左边大于右边', '左边小于右边', '两边相等', '根据题目无法判断'], rng)
  const difference = a * d - c * b
  const correct = difference > 0 ? '左边大于右边' : difference < 0 ? '左边小于右边' : '两边相等'
  return {
    method,
    stem: '比较下面两个分数的大小，选择正确关系。',
    latex: `${frac(a, b)}\\quad\\text{与}\\quad${frac(c, d)}`,
    plain: `${a}/${b} 与 ${c}/${d}`,
    options,
    answer: options.indexOf(correct),
    steps,
    pitfall,
    check: { kind: 'compare', values: [a, b, c, d] },
  }
}

function numeric(method: QuickMethod, rng: RandomSource): Omit<QuickQuestion, 'id'> {
  let target: number,
    stem: string,
    latex: string,
    plain: string,
    steps: QuickStep[],
    pitfall: string
  let candidates: number[] = [],
    unit = '',
    precision = 0
  if (method === 'growth-amount') {
    const n = [4, 5, 8, 10, 16, 20][integer(rng, 0, 5)]
    const base = integer(rng, 80, 700) * n
    const current = (base * (n + 1)) / n,
      rate = 100 / n
    target = current / (n + 1)
    stem = `现期量为 ${current}，同比增长 ${format(rate)}%，增长量最接近多少？（按整数选择）`
    latex = `\\frac{${current}\\times${format(rate)}\\%}{1+${format(rate)}\\%}`
    plain = `${current} × ${format(rate)}% ÷ (1＋${format(rate)}%)`
    steps = [
      {
        text: `增长率为 1/${n}，使用 n＋1 原则；本题增长率恰好为倒数，转换是精确的。`,
        latex: `X=\\frac{B}{n+1}=\\frac{${current}}{${n + 1}}=${target}`,
      },
    ]
    candidates = [target, current / n, current / (n - 1), current / (n + 2)]
    pitfall = '现期量×增长率会偏大；若增长率只是近似 1/n，还要结合选项间距判断近似是否足够。'
  } else if (method === 'growth-rate') {
    const base = integer(rng, 15, 100) * 1000,
      rateTenth = integer(rng, 40, 300)
    const current = base + (base * rateTenth) / 1000
    target = rateTenth / 10
    precision = 1
    unit = '%'
    stem = `基期量为 ${base}，现期量为 ${current}，同比增长率是多少？（保留一位小数）`
    latex = `\\frac{${current}-${base}}{${base}}\\times100\\%`
    plain = `(${current}－${base}) ÷ ${base} × 100%`
    steps = [
      {
        text: `增长量为 ${current - base}，除以基期量 ${base}，得到 ${format(target)}%。`,
        latex: `R=${frac(current - base, base)}=${format(target)}\\%`,
      },
    ]
    candidates = [target, ((current - base) / current) * 100, target + 5, target - 3]
    pitfall = '增长率的分母是基期量；若用现期量作分母，会把增长率算小。'
  } else {
    const base = integer(rng, 100, 900) * 10,
      rate = [5, 10, 12.5, 20, 25][integer(rng, 0, 4)]
    const current = base * (1 + rate / 100)
    target = base
    stem = `现期量为 ${format(current)}，同比增长 ${format(rate)}%，基期量最接近多少？（按整数选择）`
    latex = `\\frac{${format(current)}}{1+${format(rate)}\\%}`
    plain = `${format(current)} ÷ (1＋${format(rate)}%)`
    steps = [
      {
        text: `用现期量除以“1＋增长率”。`,
        latex: `A=\\frac{${format(current)}}{1+${format(rate)}\\%}=${base}`,
      },
    ]
    candidates = [base, current * (1 - rate / 100), current, current / (rate / 100)]
    pitfall = '现期量×(1－增长率)通常不等于基期量；增长量的基数是基期量。'
  }
  const scale = 10 ** precision
  const correct = Math.round(target * scale) / scale
  const values: number[] = []
  for (const value of candidates) {
    const rounded = Math.round(value * scale) / scale
    if (rounded >= 0 && !values.includes(rounded)) values.push(rounded)
  }
  // 明确精度后去重；补齐合理间隔，确保四项互异且唯一正确。
  for (let i = 1; values.length < 4; i++) {
    const value = correct + i * Math.max(1 / scale, Math.round(correct * 0.08 * scale) / scale)
    const rounded = Math.round(value * scale) / scale
    if (!values.includes(rounded)) values.push(rounded)
  }
  const shuffled = shuffle(values.slice(0, 4), rng)
  return {
    method,
    stem,
    latex,
    plain,
    options: shuffled.map((v) => format(v) + unit),
    answer: shuffled.indexOf(correct),
    steps,
    pitfall,
    check: { kind: 'number', target: correct, values: shuffled, unit },
  }
}

export function generateQuickSession(
  mode: QuickMode = 'mixed',
  count = 10,
  rng: RandomSource = Math.random,
): QuickQuestion[] {
  const size = Math.max(1, Math.min(30, Math.floor(count)))
  const methods =
    mode === 'mixed'
      ? shuffle(
          QUICK_METHODS.map((m) => m.id),
          rng,
        )
      : [mode]
  const questions: QuickQuestion[] = []
  const seen = new Set<string>()
  for (let attempt = 0; questions.length < size && attempt < size * 100; attempt++) {
    const method = methods[questions.length % methods.length]
    const question = ['direct', 'difference', 'position', 'split'].includes(method)
      ? comparison(method, rng)
      : numeric(method, rng)
    if (seen.has(question.latex)) continue
    seen.add(question.latex)
    questions.push({ ...question, id: `qc-${Date.now()}-${attempt}-${questions.length}` })
  }
  if (questions.length !== size) throw new Error('题目生成失败，请重新开始')
  return mode === 'mixed' ? shuffle(questions, rng) : questions
}
