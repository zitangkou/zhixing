export default defineAppConfig({
  pages: ['pages/today/index', 'pages/reading/index', 'pages/learning/example', 'pages/reading/detail', 'pages/reading/mines', 'pages/reading/terms', 'pages/training/index', 'pages/training/analyze', 'pages/training/answer', 'pages/corpus/edit', 'pages/feedback/index', 'pages/legal/index', 'pages/profile/index', 'pages/auth/login', 'pages/auth/register'],
  window: {
    navigationBarBackgroundColor: '#D0021B',
    navigationBarTitleText: '知行策论',
    navigationBarTextStyle: 'white',
    backgroundColor: '#F4F5F7',
  },
  tabBar: {
    color: '#8A8F98',
    selectedColor: '#D0021B',
    backgroundColor: '#FFFFFF',
    list: [
      { pagePath: 'pages/today/index', text: '今日', iconPath: './assets/icons/today.png', selectedIconPath: './assets/icons/today-active.png' },
      { pagePath: 'pages/reading/index', text: '精读', iconPath: './assets/icons/study.png', selectedIconPath: './assets/icons/study-active.png' },
      { pagePath: 'pages/training/index', text: '练习', iconPath: './assets/icons/practice.png', selectedIconPath: './assets/icons/practice-active.png' },
      { pagePath: 'pages/profile/index', text: '我的', iconPath: './assets/icons/profile.png', selectedIconPath: './assets/icons/profile-active.png' },
    ],
  },
})
