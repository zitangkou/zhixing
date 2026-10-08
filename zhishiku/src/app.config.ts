export default defineAppConfig({
  pages: [
    'pages/home/index',
    'pages/mine/index',
    'pages/auth/index',
    'pages/document/detail',
    'pages/legal/privacy',
    'pages/legal/terms',
  ],
  window: {
    navigationBarTitleText: '知库',
    navigationBarBackgroundColor: '#F7F8FA',
    navigationBarTextStyle: 'black',
    backgroundColor: '#F7F8FA',
    enablePullDownRefresh: true,
  },
  tabBar: {
    color: '#9A9DA4',
    selectedColor: '#DF6E60',
    backgroundColor: '#FFFFFF',
    borderStyle: 'white',
    list: [
      { pagePath: 'pages/home/index', text: '首页' },
      { pagePath: 'pages/mine/index', text: '我的' },
    ],
  },
})
