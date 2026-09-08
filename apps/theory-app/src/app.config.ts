export default defineAppConfig({
  pages: ['pages/today/index', 'pages/topics/index', 'pages/practice/index', 'pages/profile/index', 'pages/auth/login', 'pages/auth/register', 'pages/learning/article', 'pages/learning/pack', 'pages/article/detail', 'pages/article/mindmap', 'pages/question/article-pick', 'pages/question/taking', 'pages/question/wrong', 'pages/question/review', 'pages/learning/index', 'pages/learning/review', 'pages/corpus/edit', 'pages/feedback/index', 'pages/legal/index'],
  window: { navigationBarBackgroundColor: '#D0021B', navigationBarTitleText: '知行日知', navigationBarTextStyle: 'white', backgroundColor: '#F4F5F7' },
  tabBar: { color: '#8A8F98', selectedColor: '#D0021B', backgroundColor: '#FFFFFF', list: [
    { pagePath: 'pages/today/index', text: '今日', iconPath: './assets/icons/today.png', selectedIconPath: './assets/icons/today-active.png' },
    { pagePath: 'pages/topics/index', text: '专题', iconPath: './assets/icons/study.png', selectedIconPath: './assets/icons/study-active.png' },
    { pagePath: 'pages/practice/index', text: '复习', iconPath: './assets/icons/practice.png', selectedIconPath: './assets/icons/practice-active.png' },
    { pagePath: 'pages/profile/index', text: '我的', iconPath: './assets/icons/profile.png', selectedIconPath: './assets/icons/profile-active.png' },
  ] },
})
