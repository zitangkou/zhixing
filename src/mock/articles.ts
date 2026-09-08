import type { Article, ArticleSection, MindMapNode } from '@/types'
import { shiwuwuPlanArticleBase } from '@/mock/shiwuwu-plan'
import { sectionsToContent } from '@/utils/articleContent'

const createMindMap = (title: string, children: MindMapNode[]): MindMapNode => ({
  id: 'root',
  title,
  children,
})

function buildArticle(base: Omit<Article, 'content'> & { sections: ArticleSection[] }): Article {
  return {
    ...base,
    content: sectionsToContent(base.sections),
  }
}

export const mockArticles: Article[] = [
  buildArticle(shiwuwuPlanArticleBase),
  buildArticle({
    id: 'art-001',
    title: '全过程人民民主是最广泛、最真实、最管用的民主',
    source: '人民日报',
    publishDate: '2026-06-28',
    summary: '深入理解全过程人民民主的丰富内涵与制度优势。',
    tags: ['民主政治', '制度优势'],
    sections: [
      {
        id: 's1',
        title: '本质属性与制度定位',
        level: 1,
        children: [
          {
            id: 's1-1',
            title: '（一）什么是全过程人民民主',
            level: 2,
            content:
              '全过程人民民主是社会主义民主政治的本质属性，是最广泛、最真实、最管用的民主。我国全过程人民民主实现了过程民主和成果民主、程序民主和实质民主、直接民主和间接民主、人民民主和国家意志相统一。',
            highlight: '最广泛、最真实、最管用的民主',
          },
          {
            id: 's1-2',
            title: '（二）根本保证',
            level: 2,
            content:
              '坚持党的领导是发展全过程人民民主的根本保证。中国共产党始终代表最广大人民根本利益，没有任何自己特殊的利益，从来不代表任何利益集团、任何权势团体、任何特权阶层的利益。',
            highlight: '坚持党的领导是发展全过程人民民主的根本保证',
          },
        ],
      },
      {
        id: 's2',
        title: '制度体系与实现路径',
        level: 1,
        children: [
          {
            id: 's2-1',
            title: '（一）五个贯通环节',
            level: 2,
            content:
              '全过程人民民主把民主选举、民主协商、民主决策、民主管理、民主监督贯通起来，形成全面、广泛、有机衔接的人民当家作主制度体系。',
            children: [
              {
                id: 's2-1-a',
                title: '1. 民主选举',
                level: 3,
                content: '选举产生各级人大代表，保证人民依法享有选举权和被选举权。',
              },
              {
                id: 's2-1-b',
                title: '2. 民主协商',
                level: 3,
                content: '有事好商量，众人的事情由众人商量，找到全社会意愿和要求的最大公约数。',
              },
              {
                id: 's2-1-c',
                title: '3. 民主决策',
                level: 3,
                content: '集中民智、反映民意，使决策符合实际、符合民意。',
              },
            ],
          },
          {
            id: 's2-2',
            title: '（二）本质和核心',
            level: 2,
            content:
              '人民当家作主是社会主义民主政治的本质和核心。发展全过程人民民主，必须坚定不移走中国特色社会主义政治发展道路。',
            highlight: '人民当家作主是社会主义民主政治的本质和核心',
          },
        ],
      },
      {
        id: 's3',
        title: '实践要求与目标导向',
        level: 1,
        children: [
          {
            id: 's3-1',
            title: '（一）完善制度体系',
            level: 2,
            content:
              '坚持和完善我国根本政治制度、基本政治制度、重要政治制度，巩固和发展生动活泼、安定团结的政治局面。',
          },
          {
            id: 's3-2',
            title: '（二）学习备考提示',
            level: 2,
            content:
              '备考时应重点掌握"四个统一""五个贯通"等表述，准确记忆"根本保证""本质和核心"等政治术语，避免与"基本前提""关键环节"等干扰项混淆。',
          },
        ],
      },
    ],
    mindMap: createMindMap('全过程人民民主', [
      { id: 'm1', title: '本质属性', content: '社会主义民主政治的本质属性' },
      { id: 'm2', title: '根本保证', content: '坚持党的领导' },
      {
        id: 'm3',
        title: '五个贯通',
        children: [
          { id: 'm3-1', title: '民主选举', content: '选举产生各级人大代表' },
          { id: 'm3-2', title: '民主协商', content: '有事好商量' },
          { id: 'm3-3', title: '民主决策', content: '集中民智科学决策' },
        ],
      },
    ]),
  }),
  buildArticle({
    id: 'art-002',
    title: '以中国式现代化全面推进中华民族伟大复兴',
    source: '求是网',
    publishDate: '2026-06-27',
    summary: '中国式现代化的中国特色、本质要求和重大原则。',
    tags: ['中国式现代化', '伟大复兴'],
    sections: [
      {
        id: 'n1',
        title: '中国式现代化的中国特色',
        level: 1,
        children: [
          {
            id: 'n1-1',
            title: '（一）五个特色概览',
            level: 2,
            content:
              '中国式现代化是中国共产党领导的社会主义现代化，既有各国现代化的共同特征，更有基于自己国情的中国特色。',
          },
          {
            id: 'n1-2',
            title: '（二）五个特色详解',
            level: 2,
            children: [
              {
                id: 'n1-2-a',
                title: '1. 人口规模巨大',
                level: 3,
                content: '14亿多人口整体迈进现代化，规模超过现有发达国家人口总和。',
              },
              {
                id: 'n1-2-b',
                title: '2. 全体人民共同富裕',
                level: 3,
                content: '坚决防止两极分化，让现代化建设成果更多更公平惠及全体人民。',
              },
              {
                id: 'n1-2-c',
                title: '3. 两个文明相协调',
                level: 3,
                content: '物质文明和精神文明相协调，促进物的全面丰富和人的全面发展。',
              },
              {
                id: 'n1-2-d',
                title: '4. 人与自然和谐共生',
                level: 3,
                content: '走生产发展、生活富裕、生态良好的文明发展道路。',
              },
              {
                id: 'n1-2-e',
                title: '5. 走和平发展道路',
                level: 3,
                content: '推动构建人类命运共同体，创造人类文明新形态。',
              },
            ],
          },
        ],
      },
      {
        id: 'n2',
        title: '本质要求与重大原则',
        level: 1,
        children: [
          {
            id: 'n2-1',
            title: '（一）本质要求',
            level: 2,
            content:
              '中国式现代化的本质要求是：坚持中国共产党领导，坚持中国特色社会主义，实现高质量发展，发展全过程人民民主，丰富人民精神世界，实现全体人民共同富裕，促进人与自然和谐共生，推动构建人类命运共同体，创造人类文明新形态。',
          },
          {
            id: 'n2-2',
            title: '（二）五个重大原则',
            level: 2,
            content:
              '前进道路上，必须牢牢把握：坚持和加强党的全面领导，坚持中国特色社会主义道路，坚持以人民为中心的发展思想，坚持深化改革开放，坚持发扬斗争精神。',
            highlight: '五个"必须牢牢把握"是高频考点',
          },
        ],
      },
    ],
    mindMap: createMindMap('中国式现代化', [
      {
        id: 'nm1',
        title: '五个特色',
        children: [
          { id: 'nm1-1', title: '人口规模巨大', content: '14亿多人口整体迈进现代化' },
          { id: 'nm1-2', title: '共同富裕', content: '全体人民共同富裕' },
        ],
      },
      { id: 'nm2', title: '本质要求', content: '九个方面本质要求' },
      { id: 'nm3', title: '重大原则', content: '五个必须牢牢把握' },
    ]),
  }),
  buildArticle({
    id: 'art-003',
    title: '全面依法治国是国家治理的一场深刻革命',
    source: '人民日报',
    publishDate: '2026-06-26',
    summary: '习近平法治思想的核心要义与实践要求。',
    tags: ['法治建设', '国家治理'],
    sections: [
      {
        id: 'l1',
        title: '依法治国的战略意义',
        level: 1,
        children: [
          {
            id: 'l1-1',
            title: '（一）深刻革命',
            level: 2,
            content:
              '全面依法治国是国家治理的一场深刻革命，关系党执政兴国，关系人民幸福安康，关系党和国家长治久安。必须更好发挥法治固根本、稳预期、利长远的保障作用，在法治轨道上全面建设社会主义现代化国家。',
          },
        ],
      },
      {
        id: 'l2',
        title: '法治体系建设',
        level: 1,
        children: [
          {
            id: 'l2-1',
            title: '（一）三个共同推进',
            level: 2,
            content: '坚持依法治国、依法执政、依法行政共同推进。',
          },
          {
            id: 'l2-2',
            title: '（二）三个一体建设',
            level: 2,
            content:
              '坚持法治国家、法治政府、法治社会一体建设。法治政府建设是全面依法治国的重点任务和主体工程。',
          },
        ],
      },
      {
        id: 'l3',
        title: '司法公正与人民立场',
        level: 1,
        children: [
          {
            id: 'l3-1',
            title: '（一）司法公正',
            level: 2,
            content:
              '公平正义是司法的灵魂和生命。要深化司法体制综合配套改革，全面准确落实司法责任制，努力让人民群众在每一个司法案件中感受到公平正义。',
            highlight: '努力让人民群众在每一个司法案件中感受到公平正义',
          },
          {
            id: 'l3-2',
            title: '（二）以人民为中心',
            level: 2,
            content:
              '全面依法治国最广泛、最深厚的基础是人民。必须把体现人民利益、反映人民愿望、维护人民权益、增进人民福祉落实到全面依法治国各领域全过程。',
          },
        ],
      },
    ],
    mindMap: createMindMap('全面依法治国', [
      { id: 'lm1', title: '深刻革命', content: '关系执政兴国、人民安康、长治久安' },
      { id: 'lm2', title: '三个共同推进', content: '依法治国、依法执政、依法行政' },
      { id: 'lm3', title: '司法公正', content: '努力让人民群众感受到公平正义' },
    ]),
  }),
]

export const mockRankUsers = [
  { userId: 'u1', nickname: '学习达人', avatar: '', score: 2580 },
  { userId: 'u2', nickname: '理论先锋', avatar: '', score: 2340 },
  { userId: 'u3', nickname: '知行之星', avatar: '', score: 2100 },
  { userId: 'u4', nickname: '每日打卡', avatar: '', score: 1890 },
  { userId: 'u5', nickname: '知识猎人', avatar: '', score: 1650 },
  { userId: 'self', nickname: '我', avatar: '', score: 120 },
]
