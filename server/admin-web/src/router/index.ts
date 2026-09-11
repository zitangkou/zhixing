import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { canAccess, visibleNavItems } from '@/config/nav'

const router = createRouter({
  history: createWebHistory('/manage/'),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/views/Layout.vue'),
      redirect: '/articles',
      children: [
        {
          path: 'today',
          name: 'today-preview',
          component: () => import('@/views/today/Preview.vue'),
          meta: { title: '今日学员端', permissions: ['article:read', 'rmrb:read'] },
        },
        {
          path: 'articles',
          name: 'articles',
          component: () => import('@/views/articles/List.vue'),
          meta: { title: '文章管理', permissions: ['article:read'] },
        },
        {
          path: 'articles/new',
          name: 'article-new',
          component: () => import('@/views/articles/Edit.vue'),
          meta: { title: '新建文章', permissions: ['article:write'] },
        },
        {
          path: 'articles/:id',
          name: 'article-edit',
          component: () => import('@/views/articles/Edit.vue'),
          meta: { title: '编辑文章', permissions: ['article:read'] },
        },
        {
          path: 'content-ops',
          name: 'content-ops',
          component: () => import('@/views/contentOps/Index.vue'),
          meta: { title: '账号运营', permissions: ['content_ops:read'] },
        },
        {
          path: 'theory-learning',
          name: 'theory-learning',
          component: () => import('@/views/theoryLearning/Index.vue'),
          meta: { title: '时政学习入口', permissions: ['article:read'] },
        },
        {
          path: 'categories',
          name: 'categories',
          component: () => import('@/views/categories/List.vue'),
          meta: { title: '分类管理', permissions: ['article:read', 'article:write'] },
        },
        {
          path: 'users',
          name: 'users',
          component: () => import('@/views/users/List.vue'),
          meta: { title: '用户管理', permissions: ['user:read'] },
        },
        {
          path: 'knowledge',
          name: 'knowledge',
          component: () => import('@/views/knowledge/List.vue'),
          meta: { title: '知识框架', permissions: ['knowledge:read'] },
        },
        {
          path: 'plan',
          name: 'plan',
          component: () => import('@/views/plan/Templates.vue'),
          meta: { title: '学习计划', permissions: ['plan:read'] },
        },
        {
          path: 'exam',
          name: 'exam',
          component: () => import('@/views/exam/Papers.vue'),
          meta: { title: '试卷题库', permissions: ['exam:read'] },
        },
        {
          path: 'question-bank/questions',
          name: 'qb-questions',
          component: () => import('@/views/questionBank/QuestionList.vue'),
          meta: { title: '题目资产', permissions: ['exam:read'] },
        },
        {
          path: 'question-bank/questions/:id',
          name: 'qb-question-detail',
          component: () => import('@/views/questionBank/QuestionDetail.vue'),
          meta: { title: '题目详情', permissions: ['exam:read'] },
        },
        {
          path: 'question-bank/papers',
          name: 'qb-papers',
          component: () => import('@/views/questionBank/PaperList.vue'),
          meta: { title: '真题试卷', permissions: ['exam:read'] },
        },
        {
          path: 'question-bank/papers/:id',
          name: 'qb-paper-detail',
          component: () => import('@/views/questionBank/PaperDetail.vue'),
          meta: { title: '试卷详情', permissions: ['exam:read'] },
        },
        {
          path: 'generation',
          name: 'generation-index',
          component: () => import('@/views/generation/Index.vue'),
          meta: { title: '生成工作台', permissions: ['exam:read'] },
        },
        {
          path: 'generation/batches/:id',
          name: 'generation-batch-detail',
          component: () => import('@/views/generation/BatchDetail.vue'),
          meta: { title: '批次详情', permissions: ['exam:read'] },
        },
        {
          path: 'generation/review',
          name: 'generation-review',
          component: () => import('@/views/generation/Review.vue'),
          meta: { title: '教研审核', permissions: ['exam:read'] },
        },
        {
          path: 'ziliao',
          name: 'ziliao',
          component: () => import('@/views/ziliao/List.vue'),
          meta: { title: '资料分析', permissions: ['ziliao:read'] },
        },
        {
          path: 'practice/proto',
          name: 'practice-proto',
          component: () => import('@/views/practice/Proto.vue'),
          meta: { title: '练习闭环原型', permissions: ['exam:read'] },
        },
        {
          path: 'analytics/dashboard',
          name: 'analytics-dashboard',
          component: () => import('@/views/analytics/Dashboard.vue'),
          meta: { title: '学习反馈看板', permissions: ['exam:read'] },
        },
        {
          path: 'analytics/questions/:id',
          name: 'analytics-question-detail',
          component: () => import('@/views/analytics/QuestionDetail.vue'),
          meta: { title: '单题分析', permissions: ['exam:read'] },
        },
        {
          path: 'analytics/error-paths',
          name: 'analytics-error-paths',
          component: () => import('@/views/analytics/ErrorPaths.vue'),
          meta: { title: '错因归集', permissions: ['exam:read'] },
        },
        {
          path: 'rmrb',
          redirect: '/rmrb/articles',
        },
        {
          path: 'rmrb/articles',
          name: 'rmrb-articles',
          component: () => import('@/views/rmrb/ArticlesTab.vue'),
          meta: { title: '时评文章', permissions: ['rmrb:read'] },
        },
        {
          path: 'rmrb/import',
          name: 'rmrb-import',
          component: () => import('@/views/rmrb/ThreeKnifeImportTab.vue'),
          meta: { title: '三刀导入', permissions: ['rmrb:read'] },
        },
        {
          path: 'rmrb/term-categories',
          name: 'rmrb-term-categories',
          component: () => import('@/views/rmrb/TermCategoriesTab.vue'),
          meta: { title: '规范词分类', permissions: ['rmrb:read'] },
        },
        {
          path: 'rmrb/skeletons',
          name: 'rmrb-skeletons',
          component: () => import('@/views/rmrb/SkeletonsTab.vue'),
          meta: { title: '骨架模版', permissions: ['rmrb:read'] },
        },
        {
          path: 'rmrb/argument-methods',
          name: 'rmrb-argument-methods',
          component: () => import('@/views/rmrb/ArgumentMethodsTab.vue'),
          meta: { title: '论证方法', permissions: ['rmrb:read'] },
        },
        {
          path: 'rmrb/sentence-types',
          name: 'rmrb-sentence-types',
          component: () => import('@/views/rmrb/SentenceTypesTab.vue'),
          meta: { title: '句式类型', permissions: ['rmrb:read'] },
        },
        {
          path: 'corpus',
          name: 'corpus',
          component: () => import('@/views/corpus/List.vue'),
          meta: { title: '语料本', permissions: ['corpus:read'] },
        },
        {
          path: 'events',
          name: 'events',
          component: () => import('@/views/events/List.vue'),
          meta: { title: '时事事件', permissions: ['events:read'] },
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('@/views/settings/Index.vue'),
          meta: { title: '系统设置', permissions: ['setting:read', 'admin:read'] },
        },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && auth.token) {
    return { name: 'articles' }
  }
  if (!to.meta.public && auth.token && !auth.username) {
    try {
      await auth.loadMe()
    } catch {
      auth.logout()
      return { name: 'login', query: { redirect: to.fullPath } }
    }
  }
  const required = (to.meta.permissions as string[] | undefined) || []
  if (required.length && !auth.isSuperAdmin && !canAccess(auth.permissions, required)) {
    const fallback = visibleNavItems().find((item) =>
      auth.isSuperAdmin || canAccess(auth.permissions, item.permissions),
    )
    return fallback ? fallback.path : { name: 'login' }
  }
})

export default router
