export type Lesson = { id: string; stageId?: string; category: string; title: string; subtitle: string; time: string; durationMin?: number; level: string; principle: string; steps: string[]; task: string; review: string }
export type RoadmapStage = { id?: string; title: string; items: string; description?: string; sortOrder?: number; isPublished?: boolean }

export const lessons: Lesson[] = [
  { id: 'light', category: '光线', title: '先观察光，再按下快门', subtitle: '用窗边的一束光，拍出有方向的立体感', time: '12 分钟', level: '入门', principle: '光线决定画面的明暗、质感和情绪。先找光从哪里来、光有多硬，再决定人物或物体站在哪里。', steps: ['把拍摄对象放在离窗约 1 米处，先观察脸上的亮部与阴影。', '让对象慢慢转向窗户，每转一点拍一张，比较光影变化。', '锁定曝光后，试拍正面光、侧光、逆光各一张。'], task: '拍同一个对象的侧光与逆光照片各一张，选择更符合你想表达情绪的一张。', review: '亮部有没有保留细节？阴影是在塑造形体，还是遮住了重要信息？', },
  { id: 'composition', category: '构图', title: '用边缘和留白安排主体', subtitle: '从“拍全”转向“决定什么不拍”', time: '10 分钟', level: '入门', principle: '构图是对画面元素的取舍与关系安排。留白能给主体呼吸空间，也能引导视线。', steps: ['找到一个简单主体，先拍一张把它放在正中央。', '尝试把主体移到画面三分之一处，给视线方向留空间。', '检查四条边缘，移除切入画面的杂物，再拍一张。'], task: '同一场景拍“居中”和“偏置留白”两版，记录你希望观众先看见什么。', review: '主体是否一眼可辨？边缘是否有多余内容？留白有没有帮助表达？' },
  { id: 'exposure', category: '曝光', title: '曝光补偿：让相机理解你的意图', subtitle: '高调、低调和雪景不必总是灰', time: '15 分钟', level: '入门', principle: '相机会把测光区域趋向中间亮度。遇到大面积白色或黑色时，自动曝光可能把它们拍灰，需要用曝光补偿修正。', steps: ['找一处白墙或浅色物体，先用自动曝光拍摄。', '分别尝试 +1EV 与 -1EV，观察白色是否更接近现场。', '查看直方图或高光警告，避免重要亮部完全溢出。'], task: '拍一张浅色场景，分别用 -1、0、+1EV 记录效果，写下最贴近现场的一张。', review: '照片想表达明亮还是压暗？高光、阴影分别保留了多少细节？' },
  { id: 'focus', category: '对焦', title: '先确定焦点，再决定景深', subtitle: '让背景虚化服务于主体', time: '12 分钟', level: '入门', principle: '景深受光圈、焦距、拍摄距离和背景距离共同影响。只追求大光圈，可能会让主体关键部位也失焦。', steps: ['选择一个静止主体，单点对焦到最重要的细节。', '保持构图不变，用不同光圈各拍一张。', '再拉开主体与背景距离，观察虚化如何改变。'], task: '拍一组主体清晰、背景简洁的照片，至少比较两种光圈或主体背景距离。', review: '焦点落在表达重点上了吗？背景虚化是否让主体更清楚？' },
]

export const roadmap = [
  { title: '看见光', items: '光线方向 · 光质 · 色温 · 明暗关系' },
  { title: '安排画面', items: '主体与背景 · 留白 · 线条 · 层次 · 色彩' },
  { title: '控制相机', items: '曝光三要素 · 测光与曝光补偿 · 对焦 · 景深' },
  { title: '表达主题', items: '人物 · 静物 · 街景 · 风光 · 叙事与情绪' },
  { title: '形成作品', items: '选片 · 基础后期 · 系列表达 · 复盘与再拍' },
]
