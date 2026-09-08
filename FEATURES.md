# 知行公考 · 全量功能清单

> 产品名：**知行公考** · Slogan：**以「上岸」为唯一目标**
> 定位：纯公考备考应用（时政阅读、资料分析、申论、真题套卷、错题闭环），不涉及英语/读书/健康/理财等泛学习域。
> 技术：Taro 4 + Vue 3（H5 / 微信小程序）+ FastAPI + Admin（Vue 3 + Element Plus）+ SQLite
>
> ⚠️ **维护约定**：每次新增 / 优化 / 删除功能，必须同步更新本文档对应章节。
> 新增功能前先查阅本文档，防止功能重复或与全局不兼容。
> 配套开发规范见 [`PROJECT_PROMPT.md`](./PROJECT_PROMPT.md)，架构细节见 [`ARCHITECTURE.md`](./ARCHITECTURE.md)。

---

## 目录

1. [产品结构总览](#1-产品结构总览)
2. [学员端功能（按模块）](#2-学员端功能按模块)
3. [管理后台](#3-管理后台)
4. [后端能力域](#4-后端能力域)
5. [共享组件清单](#5-共享组件清单)
6. [横切能力](#6-横切能力)
7. [部署与数据备份](#7-部署与数据备份)
8. [已知缺口与未挂入口](#8-已知缺口与未挂入口)
9. [维护协议](#9-维护协议)

---

## 1. 产品结构总览

### 底部 Tab（4 个）

| Tab | 页面 | 作用 |
|-----|------|------|
| **今日** | `pages/today/index` | 今日驾驶舱：考试倒计时 + 今日清单 + 复习提醒 + 昨日足迹 + 快捷操作 |
| **学习** | `pages/index/index` | 首页：公考主线 + 时政推荐 + 复习提醒 |
| **练习** | `pages/question/index` | 刷题模式、错题、套卷、申论训练入口 |
| **我的** | `pages/user/index` | 账号、签到、积分、成长足迹、各模块折叠入口、深色模式 |

### 能力地图

```
知行公考
├── 今日驾驶舱
│   ├── 考试倒计时（目标考试设置 / 修改 / 删除）
│   ├── 今日清单（进度 + 勾选）
│   ├── 复习/内化提醒（到期任务聚合）
│   └── 昨日足迹（昨日学习 / 连续签到 / 本周累计）
├── 公考主线
│   ├── 时政阅读（文章 + 思维导图 + 出题刷题）
│   ├── 资料分析（公式库 + 题型库 + 秒杀技巧 + 专项练习）
│   ├── 申论 · 人民日报（时评 / 开采 / 词库 / 阶梯训练）
│   ├── 知识框架（考点树 + 笔记 / 星标 / 复习）
│   └── 真题套卷（开考 → 交卷 → 成绩）
├── 练习闭环
│   ├── 多种刷题模式 + 艾宾浩斯复习
│   ├── 复习中心（聚合到期任务）
│   ├── 文章错题本
│   └── 行测错题本（手动录入、图片、考点关联）
└── 成长与账号
    ├── 签到 · 积分 · 排行榜
    ├── 知行足迹（周进度聚合）
    └── 资料 · 反馈 · 深色模式
```

### 页面路由总览（53 页）

| 模块 | 页面数 | 路由前缀 |
|------|--------|----------|
| 认证 | 2 | `pages/auth/` |
| 今日 | 1 | `pages/today/` |
| 首页 | 1 | `pages/index/` |
| 时政文章 | 2 | `pages/article/` |
| 刷题练习 | 8 | `pages/question/` |
| 用户中心 | 7 | `pages/user/` |
| 语料本 | 2 | `pages/corpus/` |
| 学习计划 | 4 | `pages/plan/` |
| 知识框架 | 1 | `pages/knowledge/` |
| 事件复盘 | 2 | `pages/events/` |
| 复习中心 | 2 | `pages/review/` |
| 真题套卷 | 4 | `pages/exam/` |
| 资料分析 | 9 | `pages/ziliao/` |
| 人民日报/申论 | 7 | `pages/rmrb/` |

---

## 2. 学员端功能（按模块）

### 2.1 今日（Tab）

**路径**：`pages/today/index`

- 问候语 + 日期 + Slogan
- 考试倒计时卡（`ExamCountdownCard`）：展示距目标考试天数；点击可设置/修改/删除
- 快捷操作：签到、去练习、复习中心、足迹
- 今日清单（`TodayTaskList`）：当日计划进度 + 前 4 项任务勾选 → 完整清单
- 复习提醒（`DueReviewAlert`）：到期复习/内化数量聚合 → 复习中心
- 昨日足迹（`YesterdayBar`）：昨日学习分钟 / 连续签到 / 本周累计 → 成长页

### 2.2 学习首页

**路径**：`pages/index/index`

- 品牌渐变 Banner + 积分入口（PointsBadge）
- 快捷入口：签到、去练习、今日清单、排行
- **公考主线**：时政阅读、资料分析、申论·人民日报、知识框架、真题套卷
- 今日复习任务提醒（到期数量 → 复习中心）
- 时政必读轮播（FeaturedCarousel）+ 推荐阅读（上拉分页）

### 2.3 登录注册

**路径**：`pages/auth/login`、`pages/auth/register`

- 账号密码登录 / 注册
- 是否开放注册由服务端 `ALLOW_REGISTER` 控制（前端读 `/api/config`）

### 2.4 时政文章

**路径**：`pages/article/detail`、`pages/article/mindmap`

- 正文阅读（目录 ArticleOutline、分节翻页 SectionPager）
- 分节已读进度
- 关联知识框架 Tab
- 全屏思维导图（MindMap 组件）
- 读完可进入刷题

### 2.5 刷题练习（Tab）

**路径**：`pages/question/*`

| 页面 | 路由 | 说明 |
|------|------|------|
| 练习首页 | `index` | 刷题模式入口：今日精选 / 随机 / 时间线 / 重点突破 / 按文章练 / 错题重练 |
| 答题 | `taking` | 逐题作答 → 对错与解析 → 结果（正确率、排名、积分） |
| 按文章选题 | `article-pick` | 选择文章后进入该文章题目 |
| 复习答题 | `review` | 复习中心跳转的答题流 |
| 文章错题本 | `wrong` | 错题列表、重做、移除 |
| 行测错题列表 | `manual-list` | 手动录入错题列表；按科目筛选 |
| 行测错题练习 | `manual-quiz` | 错题重做模式 |
| 行测错题编辑 | `manual-edit` | 录入/编辑；可拍照上传图；关联知识考点；掌握标记 |

### 2.6 真题套卷

**路径**：`pages/exam/list` → `detail` → `taking` → `result`

- 筛选：真题 / 自定义 / 模拟
- 试卷详情：题目数、限时、历史 attempt
- 限时作答、交卷
- 成绩与解析、历史记录

### 2.7 资料分析

**路径**：`pages/ziliao/*`

| 页面 | 路由 | 说明 |
|------|------|------|
| 资料分析首页 | `index` | Hub：统计卡 + 公式库/题型库/技巧库/专项练习入口 |
| 公式库列表 | `formulas` | 分类筛选 chips + 公式卡片（LatexBlock 渲染） |
| 公式详情 | `formula-detail` | 公式 + 白话释义 + 例题 |
| 题型库列表 | `types` | 题型分类浏览 |
| 题型详情 | `type-detail` | 题型说明 + 解题步骤 |
| 秒杀技巧列表 | `tricks` | 技巧分类浏览 |
| 技巧详情 | `trick-detail` | 技巧说明 + 适用场景 + 示例 |
| 专项练习 | `drill` | 进度圆点 + 材料折叠 + 逐题作答 + 计时 + 底部导航 |
| 练习结果 | `result` | 分数卡 + 正确率 + 错题解析 + 重做/错题本/返回 |

### 2.8 知识框架

**路径**：`pages/knowledge/index`

- 多棵考点树切换与浏览（KnowledgeTree 组件）
- 节点操作：备注、标重点、掌握度
- 知识点复习（SRS 间隔重复）
- 数据可由 Obsidian Markdown 同步（管理端上传 / 服务端 sync）

### 2.9 复习中心

**路径**：`pages/review/hub`、`pages/review/quiz`

- 聚合到期复习任务（文章错题、手动错题、知识点）
- 按来源分组展示
- 进入复习答题流

### 2.10 学习计划

**路径**：`pages/plan/today`、`week`、`day`、`review`

| 页面 | 说明 |
|------|------|
| 今日清单 | 完成 / 跳过、备注、增删临时任务 |
| 今日复盘 | 完成度、弱项、明日重点、心情 |
| 本周总览 | 按日查看 |
| 按日详情 | 单日任务列表 |

- 模板由管理端按「星期」配置，可复制到另一天

### 2.11 事件复盘

**路径**：`pages/events/index`、`pages/events/edit`

- 事件列表（时间线）
- 录入/编辑：标题、日期、地点、核心内容、补充联想
- 语音输入（VoiceInputBtn）
- 归属知识框架（KnowledgePointPicker）
- 删除二次确认

### 2.12 人民日报 / 申论

**路径**：`pages/rmrb/*`

| 页面 | 路由 | 说明 |
|------|------|------|
| 学习概览 | `index` | 本周开采天数、规范词、今日状态 |
| 时评列表 | `article-list` | 时评文章浏览 |
| 时评详情 | `article-detail` | 阅读 + 结构化解剖 |
| 开采本 | `mines` | 按日记录论点/规范词/骨架等 |
| 开采编辑 | `mine-edit` | 编辑开采记录 |
| 规范词库 | `terms` | 学习 / 掌握状态 |
| 阶梯训练 | `drill` | 造句 · 仿写 · 口述 |

独立申论应用 `apps/shenlun-app` 已按原版迁移完整三刀解剖核心：骨架、规范词、金句、动词、句式五模块，保留分类/模板、动态增删、语音输入、分模块保存、历史恢复和删除；小题作答、自检与表达沉淀恢复为拆解后的独立页面。开采本、规范词库、阶梯训练也已恢复原版页面结构、字段、接口和交互；文章详情已恢复复制全文、正文选择/快捷记入语料、阅读进度与三刀入口，并接通原文、澄清、改写、运用四步语料编辑及知识框架归属。

独立政治理论应用 `apps/theory-app` 已按原版拆回四段学习闭环：读前两道第一判断恢复为独立“读前定向”页，答题后的原文依据、错题筛选、逐题错因与完成状态恢复为独立“错因与依据”页；答题结果同时保存用户答案、错题 ID 和正确率，保证复盘页字段与原版一致。原文精读已恢复多层目录、目录/翻页模式、逐节已读进度、知识框架及全屏视图、复制正文和语料采集，并复用共享后端的分节阅读记录。通用证据刷题已恢复随机练、按文章选题、原版题目组件、单选即时判定、多选确认、解析与原文依据、上下题、退出/重开确认、结果统计和错题写入；错题本已恢复待复习/已安排/全部筛选、按文章分组、SRS 档位与到期时间、单题重做、今日批量复习和移除确认。到期文章复习与套卷入口继续按基线迁移。

### 2.13 语料本

**路径**：`pages/corpus/index`、`pages/corpus/edit`

- 语料采集（CorpusSelectCapture 组件：选中文字 → 采集）
- 标签、来源、知识点挂载
- 沉淀到规范词

### 2.14 我的 · 成长与账号

**路径**：`pages/user/*`

| 页面 | 路由 | 说明 |
|------|------|------|
| 我的首页 | `index` | 头像/昵称 + 签到/积分/排行快捷 + 各模块折叠入口 + 深色模式开关 |
| 个人资料 | `profile` | 头像（≤2MB）、昵称/邮箱/手机、改密 |
| 签到 | `signin` | 日历（SignCalendar）、连续天数、积分 |
| 积分明细 | `points` | 收入/支出流水 |
| 刷题排行 | `rank` | 日 / 周 / 月 / 总（RankList） |
| 知行足迹 | `growth` | 签到/本周分钟/正确率/积分；五领域进度条；本周投入柱状图 |
| 反馈建议 | `feedback` | 提交文本 |

---

## 3. 管理后台

**访问**：部署后 `https://域名/manage/`（本地 `admin-web` 开发服）

| 菜单 | 能力 |
|------|------|
| 文章管理 | 列表/筛选；新建编辑；Markdown 导入；置顶/今日推荐；审核发布；题目 CRUD / AI 出题 / 导入 / 批量审核 |
| 分类管理 | 分类树 CRUD |
| 用户管理 | 学员列表（积分、状态等） |
| 知识框架 | 上传 md、树与节点、同步状态、删树 |
| 学习计划 | 按星期的任务模板；复制到另一天；启停 |
| 试卷题库 | 真题/自定义/模拟卷与题目；导入上传 |
| 资料分析 | 公式、题型、秒杀技巧、练习资源 |
| 人民日报 | 时评文章、规范词分类、骨架模版、句式类型、论证方法 |
| 语料本 | 语料列表、状态 / 类型筛选（收件箱 → 已澄清 → 已内化 → 已运用） |
| 时事事件 | 事件列表、按用户检索、编辑 / 删除 |
| 系统设置 | `SystemSetting` 键值编辑；角色权限矩阵（只读） |

管理员独立登录（与学员 JWT 分离），RBAC 权限矩阵。

---

## 4. 后端能力域

公开前缀：`/api`（需登录的接口走 App JWT）

| 域 | 代表能力 |
|----|----------|
| 配置/认证 | 公开配置、注册、登录 |
| 用户 | 资料、改密、头像上传 |
| 文章/刷题 | 日更与推荐、答题、错题、测验完成与排行 |
| 学习记录 | 阅读记录、分节已读 |
| 签到积分 | 签到、积分、流水、总榜 |
| 倒计时 | `GET/PUT/DELETE /api/countdown` 目标考试 |
| 行为事件 | `activity_events` 表 + `activity_service.record_event`（M4 统计底座，仅写入） |
| 复习 | 复习任务列表与完成（SRS 间隔重复） |
| 计划 | 今日/周/日清单、任务 CRUD、日复盘 |
| 知识 | 树列表、详情、同步、节点更新、知识点复习 |
| 行测错题 | CRUD + 图片上传 |
| 套卷 | 试卷、开考、作答、交卷、历史 |
| 资料分析 | 公式/题型/技巧 CRUD、专项练习、提交、结果 |
| 申论 RMRB | 元数据、统计、时评、开采、词库、训练、骨架模版 |
| 语料本 | 语料 CRUD、标签、知识点挂载 |
| 事件复盘 | 事件 CRUD、知识框架关联 |
| 足迹 | `GET /api/growth/overview` |

管理端前缀：`/admin`（文章、用户、知识、计划、试卷、资料分析、人民日报、设置、角色等）。

---

## 5. 共享组件清单

| 组件 | 文件 | 用途 | 使用页面 |
|------|------|------|----------|
| AppTabBar | `AppTabBar.vue` | 自定义底部 TabBar（4 tab） | 今日、首页、练习、我的 |
| AppFeedback | `AppFeedback.vue` | 全局 Toast / Confirm 宿主 | AppTabBar 内嵌（小程序）/ body 挂载（H5） |
| ExamCountdownCard | `today/ExamCountdownCard.vue` | 考试倒计时卡（展示/编辑） | 今日 |
| TodayTaskList | `today/TodayTaskList.vue` | 今日清单预览 | 今日 |
| DueReviewAlert | `today/DueReviewAlert.vue` | 复习/内化到期提醒 | 今日 |
| YesterdayBar | `today/YesterdayBar.vue` | 昨日足迹汇总 | 今日 |
| ArticleCard | `ArticleCard.vue` | 文章卡片 | 首页推荐、文章列表 |
| ArticleOutline | `ArticleOutline.vue` | 文章目录 | 文章详情 |
| ArticleSections | `ArticleSections.vue` | 文章分节内容 | 文章详情 |
| SectionPager | `SectionPager.vue` | 分节翻页器 | 文章详情 |
| BrandLogo | `BrandLogo.vue` | 品牌 Logo | 登录、首页 |
| CorpusSelectCapture | `CorpusSelectCapture.vue` | 选中文字采集 | 语料本 |
| FeaturedCarousel | `FeaturedCarousel.vue` | 必读轮播 | 首页 |
| KnowledgeTree | `KnowledgeTree.vue` | 知识树递归展示 | 知识框架 |
| KnowledgePointPicker | `KnowledgePointPicker.vue` | 知识点选择弹层 | 事件编辑、错题编辑 |
| LatexBlock | `LatexBlock.vue` | KaTeX 公式渲染 | 资料分析公式页 |
| MindMap | `MindMap.vue` | 思维导图 | 文章思维导图 |
| PointsBadge | `PointsBadge.vue` | 积分徽章 | 首页 Banner |
| QuestionItem | `QuestionItem.vue` | 题目卡片 | 答题、错题 |
| RankList | `RankList.vue` | 排行榜列表 | 排行页 |
| SignCalendar | `SignCalendar.vue` | 签到日历 | 签到页 |
| VoiceInputBtn | `VoiceInputBtn.vue` | 语音输入按钮 | 开采编辑、阶梯训练、语料本、事件编辑 |
| WheelPicker | `WheelPicker.vue` | 滚轮选择器 | 开采编辑、规范词库 |

---

## 6. 横切能力

| 主题 | 说明 |
|------|------|
| 鉴权 | 学员 JWT；管理员独立 token；RBAC 权限矩阵 |
| 积分规则 | 签到/阅读/答对等；部分基数可在系统设置里配 |
| 深色主题 | CSS 变量（`--zk-*`）+ `theme-dark` class + 「我的」开关；`utils/theme.ts` 同步原生壳 |
| 品牌色 | 5 套主题、默认中国红 `#D0021B`（深蓝 / 墨绿 / 靛紫 / 琥珀橙可选）；CSS 变量 `--zk-*` 运行时切换；`useBrandColor()` 供图标 props |
| 媒体文件 | 头像、错题图 → `data/uploads/`（**不进 SQLite**） |
| Mock 模式 | `USE_MOCK=true npm run dev:h5` 走本地 Mock；默认连真实 API |
| LLM | `llm_enabled` 控制 AI 出题等，默认关闭 |
| 爬虫 | 已彻底删除（见 OPTIMIZATION.md P1） |
| 注册开关 | 生产建议 `ALLOW_REGISTER=false` |
| 反馈系统 | `utils/platform.ts`：showToast / showConfirm / promptText / copyText（禁止直接调 Taro.showToast） |
| 导航封装 | `utils/platform.ts`：navigateTo / switchTab |
| 表单防丢 | `utils/formFlush.ts`：保存前 flush 语音输入 |
| 记忆曲线 | `utils/memoryCurve.ts`：SRS 间隔重复计算 |

---

## 7. 部署与数据备份

详见 [`DEPLOY.md`](./DEPLOY.md)（本地开发启动、Docker 发版、**整包 data 备份与恢复**）。

要点：

- 生产数据在 Docker 卷中：`zhengkao.db` + `uploads/` + `knowledge/`
- 只备份库文件会丢图片；请整包 tar
- 服务器 cron 日备 + 本机/网盘异地
- **禁止** `docker compose down -v`（会删卷）

---

## 8. 已知缺口与未挂入口

| 项 | 现状 |
|----|------|
| 爬虫 | 已彻底删除（如需自动抓取需重建，见 OPTIMIZATION.md） |
| 支付 | 无真实微信/支付宝对接（原充值页已整体移除） |
| 足迹 Admin | 无管理端入口（用户侧数据为主） |
| 行为事件统计 | `activity_events` 已埋点写入（7 处），但无统计/可视化页面（M4：上岸卡片 / 能力雷达 / 里程碑） |
| 质量与架构债 | lint 门禁已通过（当前 0 errors、85 warnings）、核心闭环测试已补齐（21 passed）、CI 已接入；残留项见 [OPTIMIZATION.md](./OPTIMIZATION.md) |

---

## 9. 维护协议

> **每次功能变更必须执行以下流程，防止功能重复或全局不兼容。**

### 9.1 新增功能前

1. **查本文档**：确认是否已有相同/相似功能（查能力地图 + 页面路由总览）
2. **查 PROJECT_PROMPT.md**：确认布局、样式、交互遵循全局规范
3. **查 app.config.ts**：确认路由未重复
4. **查共享组件清单**：优先复用，禁止重复造轮子

### 9.2 新增/优化/删除功能后

1. **更新本文档**：
   - 能力地图（§1）：新增/调整节点
   - 页面路由总览（§1）：更新页面数
   - 对应模块章节（§2）：补充页面表格或修改说明
   - 管理后台（§3）：如有新菜单
   - 后端能力域（§4）：如有新 API 域
   - 共享组件清单（§5）：如有新组件
   - 已知缺口（§8）：如修复了缺口或产生新缺口
2. **更新 PROJECT_PROMPT.md**：如涉及新的交互模式或布局类型
3. **更新 ARCHITECTURE.md**：如涉及新的数据模型或服务层

### 9.3 快速对照入口

| 想了解 | 看哪里 |
|--------|--------|
| 全部页面 | `src/app.config.ts` → `pages` 数组 |
| 全部组件 | `src/components/` 目录 |
| 全部 Store | `src/store/` 目录 |
| 后台菜单 | `server/admin-web/src/config/nav.ts` |
| 后台路由 | `server/admin-web/src/router/index.ts` |
| API 接口 | `src/api/index.ts`（学员端）/ `server/app/api/`（后端） |
| 数据模型 | `server/app/models/__init__.py` |

---

*最后更新：2026-08-22 · 基于 app.config.ts 53 个页面路由 + 24 个共享组件复核；优化与后续路线见 [OPTIMIZATION.md](./OPTIMIZATION.md)*
