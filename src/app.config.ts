export default defineAppConfig({
  // 主包：启动页 + tabBar。pages/user 含 tab，不能整目录做分包根。
  pages: [
    'pages/index/index',
    'pages/user/index',
    'pages/user/profile',
    'pages/user/signin',
    'pages/user/points',
    'pages/user/rank',
    'pages/user/growth',
    'pages/user/feedback',
    'pages/user/data',
  ],
  subPackages: [
    {
      root: 'pages/today',
      pages: ['index'],
    },
    {
      root: 'pages/auth',
      pages: ['login', 'register'],
    },
    {
      root: 'pages/article',
      pages: ['detail', 'mindmap'],
    },
    {
      root: 'pages/question',
      pages: [
        'index',
        'taking',
        'xingce-hub',
        'xingce-modules',
        'xingce',
        'theory-packs',
        'article-pick',
        'review',
        'wrong',
        'manual-list',
        'manual-quiz',
        'manual-edit',
      ],
    },
    {
      root: 'pages/corpus',
      pages: ['index', 'edit'],
    },
    {
      root: 'pages/plan',
      pages: ['today', 'review', 'week', 'day'],
    },
    {
      root: 'pages/knowledge',
      pages: ['index'],
    },
    {
      root: 'pages/events',
      pages: ['index', 'edit'],
    },
    {
      root: 'pages/review',
      pages: ['hub', 'quiz'],
    },
    {
      root: 'pages/exam',
      pages: ['list', 'detail', 'taking', 'result'],
    },
    {
      root: 'pages/ziliao',
      pages: [
        'index',
        'formulas',
        'formula-detail',
        'types',
        'type-detail',
        'tricks',
        'trick-detail',
        'drill',
        'result',
      ],
    },
    {
      root: 'pages/rmrb',
      pages: [
        'index',
        'article-list',
        'article-detail',
        'mines',
        'mine-edit',
        'terms',
        'drill',
      ],
    },
    {
      root: 'pages/shenlun',
      pages: ['training'],
    },
  ],
  // 按需注入自定义组件，降低主包/页面注入开销（质量审计项）
  lazyCodeLoading: 'requiredComponents',
  window: {
    navigationBarBackgroundColor: '#D0021B',
    navigationBarTitleText: '知行公考',
    navigationBarTextStyle: 'white',
    backgroundColor: '#F3F4F6',
  },
  tabBar: {
    color: '#999999',
    selectedColor: '#D0021B',
    backgroundColor: '#FFFFFF',
    borderStyle: 'white',
    list: [
      // H5 开发态会误删 iconPath 首字符（assets → ssets），必须写 ./ 前缀；
      // 生产构建会自动改写并打包到 /static/images/*.png
      {
        pagePath: 'pages/index/index',
        text: '学习',
        iconPath: './assets/icons/home.png',
        selectedIconPath: './assets/icons/home-active.png',
      },
      {
        pagePath: 'pages/user/index',
        text: '我的',
        iconPath: './assets/icons/user.png',
        selectedIconPath: './assets/icons/user-active.png',
      },
    ],
  },
})
