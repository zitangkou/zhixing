export default defineAppConfig({
  pages: ['pages/home/index', 'pages/scenes/index', 'pages/mine/index', 'pages/lesson/index'],
  window: {
    navigationBarTitleText: '言遇英语',
    navigationBarBackgroundColor: '#F6F7F3',
    navigationBarTextStyle: 'black',
    backgroundColor: '#F6F7F3',
  },
  tabBar: {
    color: '#89928E',
    selectedColor: '#256D73',
    backgroundColor: '#FFFFFF',
    list: [
      { pagePath: 'pages/home/index', text: '今日', iconPath: './assets/icons/today.png', selectedIconPath: './assets/icons/today-active.png' },
      { pagePath: 'pages/scenes/index', text: '场景', iconPath: './assets/icons/scenes.png', selectedIconPath: './assets/icons/scenes-active.png' },
      { pagePath: 'pages/mine/index', text: '我的', iconPath: './assets/icons/mine.png', selectedIconPath: './assets/icons/mine-active.png' },
    ],
  },
})
