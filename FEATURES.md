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

> **当前学员端菜单**：对外只露出时政文章学习/刷题与时评精拆（三刀申论）。开关见 `src/constants/featureVisibility.ts`。隐藏模块路由仍注册，深链可进。

---

## 1. 产品结构总览

### 底部 Tab（2 个）

| Tab | 页面 | 作用 |
|-----|------|------|
| **学习** | `pages/index/index` | 今日文章（评论/理论） |
| **我的** | `pages/user/index` | 账号、签到、积分、排行、时评精拆、文章错题、设置 |

今日（`pages/today/index`）、练习（`pages/question/index`）路由仍注册，不挂 Tab。

### 当前对外露出（菜单）

对齐公众号「时政学习 / 申论学习」两块。开关：`src/constants/featureVisibility.ts`。

**露出**

- 时政：卡片列表 → 读原文（HTML 优先）→ 读完再练习；错题从「我的」进
- 申论：时评列表 → 读原文 HTML → 时评解析 HTML；开采从详情「去开采」
- 账号：登录注册、签到、积分、排行、主题/深色、反馈（数据导入导出页保留路由，菜单已关）

**菜单隐藏（路由保留，新入口先复用再开开关）**

| 隐藏项 | 复用位置 |
|--------|----------|
| 学习页「学习入口」宫格 | `SHOW_HOME_DOMAINS` + `examDomains` |
| 时政必读轮播 | `FeaturedCarousel` 仍在，首页未挂 |
| 时评枢纽（开采/词库/阶梯） | `pages/rmrb/index`，快捷区已改走时评列表 |
| 按文章直练 | 旧 `article-pick` 直跳 `taking` 已改为先详情 |
| 今日 / 练习 Tab | `pages/today/index`、`pages/question/index` |
| 随机刷题 | 练习页深链 `taking?mode=random` |
| 资料分析、真题套卷、知识框架、时事印象、计划清单、混合复习中心、行测错题、语料本、知行足迹、考试倒计时 | `featureVisibility.ts` 对应 `SHOW_*` |

### 能力地图（全量能力，含已隐藏）

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

### 2.1 今日（非 Tab）

**路径**：`pages/today/index`（深链可进）

- 问候语 + 日期 + Slogan
- 主入口：按文章练、时评精拆
- 快捷：签到、练习（按文章练）

### 2.2 学习首页（Tab）

**路径**：`pages/index/index`

- Banner 品牌；快捷「时政练习」→ 时政阅读列表（`article-pick`）；快捷「时评精拆」→ 时评原文列表
- **今日文章**：合并评论（时评）与理论（时政）卡片，标签「评论 / 理论」，按发布日期再 `createdAt` 排序。优先后台「今日推荐」（`is_daily`，可多篇）；两边都没有推荐时各取最近 1 篇兜底
- 全库预览不在首页；从快捷入口进入
- 时评：先读原文 HTML；底栏「时评解析」有 `displayHtml` 才渲染精拆 HTML，否则提示后台导入解析
- 时政：详情页全文阅读（一页下滚）；点「完成阅读」后可答题
- **学习入口**宫格：`SHOW_HOME_DOMAINS=false`

### 2.3 登录注册

**路径**：`pages/auth/login`、`pages/auth/register`

- 账号密码登录 / 注册
- 是否开放注册由服务端 `ALLOW_REGISTER` 控制（前端读 `/api/config`）

### 2.4 时政文章

**路径**：`pages/article/detail`、`pages/article/mindmap`

- 全文阅读：有 HTML 时页内渲染（跟主题底色）；否则本页连续展示 `content` 或拼接小节
- 知识框架 Tab 已隐藏（`pages/article/mindmap` 深链仍可进）
- 底栏：完成阅读、考点练习（不再复制正文 / 记入语料）
- 考点练习进入该文刷题

### 2.5 刷题练习（非 Tab）

**路径**：`pages/question/*`

| 页面 | 路由 | 说明 |
|------|------|------|
| 练习首页 | `index` | 时政刷题（随机 / 按文章练）+ 文章错题 + 申论阶梯训练；资料分析 / 套卷 / 行测错题菜单已关 |
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
| 时评详情 | `article-detail` | 标题/来源/日期/主题头 + 原文 HTML；解析仅在有 `displayHtml` 时渲染，否则提示导入 |
| 开采本 | `mines` | 按日记录论点/规范词/骨架等 |
| 开采编辑 | `mine-edit` | 编辑开采；下拉 = 启用词表 ∪ 本篇已有未入表名字 |
| 规范词库 | `terms` | 学习 / 掌握状态 |
| 阶梯训练 | `drill` | 造句 · 仿写 · 口述 |

申论能力在综合端内完成：三刀解剖（骨架、规范词、金句、动词、句式）、开采本、规范词库、阶梯训练、小题作答（`pages/shenlun/training`）。时政阅读走文章详情与刷题，不另开垂直 H5。词表（规范词/动词分类、骨架、论证方法、句式）存在独立表里，种子只补缺；新文里尚未入表的名字进 `vocab_inbox`，后台人工收录，不会从整篇 HTML 自动建节点。

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

**访问**：部署后 `https://域名/manage/`（本地 `http://localhost:5173/manage/`）

**当前侧栏露出**（开关 [`server/admin-web/src/config/featureVisibility.ts`](server/admin-web/src/config/featureVisibility.ts)，与学员端两块主线对齐；隐藏页路由仍可直开）：

| 菜单 | 能力 |
|------|------|
| **时政考点** · 文章管理 | 列表带 HTML/结构化标记；Markdown / **HTML 导入**（可填摘要、标签、来源）；今日推荐可多篇；审核发布；题目 CRUD |
| **时政考点** · 分类管理 | 时政分类树 CRUD；顶栏 **待收录**（推断失败时的标签名，晋升为「未归类」下叶子） |
| **时评精拆** · 时评文章 | 原文 HTML；摘要/主题/来源/日期/链接可填（空则从 HTML 抽）；今日推荐/发布；行内 **导入解析** |
| **时评精拆** · 规范词 / 骨架 / 论证方法 / 句式 | 各表 CRUD；顶栏 **待收录**（开采保存或 Markdown 三刀导入扫到的未知名字 → 收录或忽略） |
| 用户管理 | 学员列表（积分、状态等） |
| 系统设置 | `SystemSetting` 键值编辑；角色权限矩阵（只读） |

**侧栏隐藏（路由保留）**：账号运营、时政学习入口、知识框架、学习计划、试卷题库、题目资产、真题试卷、生成工作台、教研审核、资料分析、练习闭环原型、反馈看板、错因归集、语料本、时事事件。三刀 Markdown 导入接口仍在，侧栏不再单独挂「三刀导入」页。

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
| 申论 RMRB | 元数据、统计、时评 HTML、开采、词库、训练、骨架模版、`vocab_inbox` 待收录 |
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
| 学习页隐藏入口 | 「学习入口」宫格、时政必读轮播未挂菜单；新规划先复用 `examDomains` / `FeaturedCarousel`，见 §1 隐藏表 |
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

*最后更新：2026-09-09 · 时评元数据对齐、理论全文阅读、主题持久化、阅读页去 iframe*
