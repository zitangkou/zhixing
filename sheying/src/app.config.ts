export default defineAppConfig({
  pages: ['pages/home/index', 'pages/courses/index', 'pages/lesson/index', 'pages/practice/index', 'pages/mine/index'],
  window: { navigationBarTitleText: '光线练习簿', navigationBarBackgroundColor: '#f4f1eb', navigationBarTextStyle: 'black', backgroundColor: '#f4f1eb' },
  tabBar: {
    color: '#88877f', selectedColor: '#315e52', backgroundColor: '#fbfaf7', borderStyle: 'white',
    list: [{ pagePath: 'pages/home/index', text: '学摄影' }, { pagePath: 'pages/mine/index', text: '我的练习' }],
  },
})
