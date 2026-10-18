# 知行公考项目架构与业务功能梳理

> 更新时间：2026-10-11
> 项目定位：纯公考备考应用（时政阅读、资料分析、申论、真题套卷、错题闭环、今日驾驶舱）。

## 1. 系统总览

本仓库由多个独立学员端工程、共享 API 和共享管理后台组成：

| 部分 | 目录 | 技术栈 | 职责 |
| --- | --- | --- | --- |
| 知行主学员端 | 根目录 `src/` | Taro 4、Vue 3、TypeScript、NutUI、Pinia | 主 H5 与知行微信小程序；公考学习、练习、复盘、个人中心 |
| 独立小程序 | `baibaoxiang/`、`zhishiku/`、`kaikoushuo/`、`sheying/` | 各自的 Taro 工程和微信 AppID | 百宝箱、知库、言遇英语、光线练习簿；前端构建与发布独立 |
| 后端 API | `server/app/` | FastAPI、SQLAlchemy 2、SQLite、JWT | 共享业务接口、数据持久化、鉴权、文件上传、启动初始化 |
| 管理后台 | `server/admin-web/` | Vue 3、Vite、Element Plus、Pinia | 所有产品共用的内容、题库、用户、配置、权限和资源管理 |

整体形态是一个单体仓库：多个独立客户端 + 一套 FastAPI + 一套管理后台。独立小程序分别拥有项目目录、AppID、客户端本地状态和发布版本；服务端和数据库共享。API 使用产品 Header 和微信 AppKey 选择产品上下文及登录凭据，不应把“独立发布”误认为“独立后端/数据库”。

```text
知行 H5 / 各独立微信小程序
        |
        | /api/*
        v
FastAPI 后端 ---- SQLite / data/uploads
        ^
        | /admin/*
管理后台 Vue 应用
```

生产 Docker 镜像会构建知行主 H5、构建共享管理后台，然后由 FastAPI 提供 `/api/*`、`/admin/*`、上传文件与 `/manage/`。独立小程序由各自工程单独构建并上传到微信平台。全仓产品和操作矩阵见 [`docs/PROJECT_OPERATIONS_MANUAL.md`](./docs/PROJECT_OPERATIONS_MANUAL.md)。

## 2. 技术架构

### 2.1 学员端

学员端位于 `src/`，使用 Taro 跨端运行：

- `src/app.config.ts`：声明全部页面路由、窗口样式；H5 保留原生路由 Tab 配置，微信端由单页容器承载两个主 Tab。
- `src/app.ts`：创建 Vue 应用、安装 Pinia、接入持久化、本地主题初始化和应用启动 bootstrap。
- `src/api/index.ts`：统一 API 客户端，负责真实 API / Mock 切换、Token 注入、401 处理、上传入口。
- `src/pages/`：业务页面，按模块拆分。
- `src/components/`：公共组件，如文章卡片、知识树、题目项、思维导图、反馈层、积分徽章等。
- `src/store/`：Pinia 状态，覆盖用户、题目、文章、计划、设置、知识、手动错题等。
- `src/utils/`：跨模块工具，如鉴权、媒体 URL、上传、记忆曲线、语音输入、知识树等。
- `src/mock/service.ts`：`USE_MOCK=true` 时的本地演示服务。

底部 Tab 有两个主入口。微信端由 `pages/index/index` 挂载 `StudyHomePanel` 与 `StudyUserPanel`，`AppTabBar` 只切换面板状态，不调用 `switchTab`；H5 保留独立首页/个人页路由。`pages/user/index` 在微信端作为旧路径兼容跳转，登录回跳通过 `?tab=user` 恢复目标面板。

| Tab | 页面 | 业务定位 |
| --- | --- | --- |
| 学习 | `pages/index/index` | 学习入口、时评原文、时政必读与推荐 |
| 我的 | `pages/user/index` | 账号、签到、积分、排行、主题和设置 |

### 2.2 后端

后端位于 `server/app/`：

- `main.py`：FastAPI 应用入口，注册 CORS、公开路由、管理路由、上传目录和管理后台静态资源。
- `api/public/`：学员端接口（按域拆分：auth_user / article_quiz / plan / knowledge / manual_wrong / exam / rmrb / corpus / events / ziliao / countdown），`routes.py` 聚合，统一前缀 `/api`。
- `api/admin/`：管理端接口（按域拆分 13 个文件），`routes.py` 聚合，统一前缀 `/admin`。
- `models/`：SQLAlchemy ORM 模型（base + 11 个域模块），`__init__.py` 统一 re-export。
- `schemas/`：Pydantic 入参和出参结构（按域拆分 16 个模块，`__init__.py` 统一 re-export）。
- `services/`：业务服务层，承载主要业务规则。
- `core/`：权限、响应结构、安全工具。
- `database.py`：数据库连接和 Session 管理。
- `config.py`：环境变量配置。
- `seed.py`：默认数据初始化。
- `upload_paths.py`：上传目录管理。

后端启动时会执行：

- `Base.metadata.create_all()` 创建表。
- 对旧 SQLite 表做兼容补列。
- 初始化默认管理员、默认内容、计划模板、资料分析资源。
- 尝试从 Obsidian Markdown 同步知识框架。

### 2.3 管理后台

管理后台位于 `server/admin-web/`：

- `src/router/index.ts`：管理端路由。
- `src/config/nav.ts`：侧边栏菜单和权限控制。
- `src/api/`：管理端接口封装。
- `src/views/`：各业务管理页面。
- `src/stores/auth.ts`：管理员登录状态。

管理后台菜单包括：

| 菜单 | 职责 |
| --- | --- |
| 时政考点 · 文章管理 | 文章 CRUD、Markdown/HTML 导入、审核发布、分类、题目管理、AI 出题 |
| 时政考点 · 分类管理 | 时政分类树；待收录晋升叶子 |
| 时评精拆 | 时评原文 HTML、解析 HTML、规范词/骨架/句式/论证方法；词表待收录 |
| 时政要点 | TheoryPoint 编排已发布原文及题目；管理接口支持分页查询，Article 保存 brief_json / brief_status，学员端仅取已发布要点。时政套题用 ArticleQuizProgress 保存用户进度与最近作答。 |
| 人民日报 | 每日金句库、词汇素材库、申论素材库分表管理。申论四类练习由 `ShenlunExercise` 管理，定时生成批次由 `ShenlunExerciseJob` 管理。生成任务复用48小时 `RmrbDailyPoolArticle` 与联合分析缓存，按公共议题/治理/政策材料锚点筛选、正文去重，每批最多处理3篇，并记录逐篇进度与已完成候选供续跑；通过原文证据、字数硬校验及结构化复核后只存草稿；生成和复核均参考`shenlun_benchmark_cases.json`中按教材真题结构整理的8个题型样例，并记录基准集版本。人工审核后发布；审核结论、问题维度、意见、修改标记保存在质量报告并留存变更历史；`/admin/shenlun-exercises/review-metrics`按审核结果、题型和问题维度汇总反馈；审核历史保存当时的题目内容快照，`/admin/shenlun-exercises/review-dataset`支持筛选和分页导出审核样本 JSON；反馈统计按生成规则版本聚合审核结果与修改数，`server/scripts/analyze_shenlun_review_dataset.py`将审核事件样本汇总为本地复盘报告。旧规则草稿标为需复核。公开接口仅返回已发布题，首次提交后才返回解析；`ShenlunExerciseAttempt` 保存作答、订正和反思，行为事件经 `activity_service.record_event()` 写入。 |
| 用户管理 | 学员账号、积分、状态管理 |
| 知识框架 | Markdown 上传、树同步、节点维护；工作台可将当前已保存结构化草稿导出为 Markdown、阅读版 HTML（图片引用原资源地址）或 Markmap 渲染 PNG（长边上限 4096 像素） |
| 学习计划 | 周计划模板维护、同步到待办 |
| 试卷题库 | 试卷、题目、批量导入 |
| 资料分析 | 公式、题型、秒杀技巧、练习资源 |
| 系统设置 | 键值配置、角色权限矩阵 |

### 2.4 独立小程序：言遇英语视听课程

言遇英语客户端独立位于 `kaikoushuo/`，课程数据由共享英语 API 和管理后台提供；详细产品边界与发布流程见 [`docs/PROJECT_OPERATIONS_MANUAL.md`](./docs/PROJECT_OPERATIONS_MANUAL.md)。

- `EnglishUnit.content_json` 保存媒体、台词/字幕、核心句块和口语任务，不新增数据库列，旧课程兼容。
- 已发布课程目录包含学习所需内容；课程可配置视频/音频、官方来源及授权状态。
- 管理后台发布校验：直播放地址需标记 `licensed_hosting`；仅外链素材记录 `sourceUrl`，小程序展示复制来源入口；待核验或不可用内容不能带媒体发布。
- 小程序在授权状态允许且有媒体 URL 时播放音视频；提供中文释义显示控制、口语任务、本地录音回放和完成记录。
- 当前课程素材库仍处于早期阶段：线上已发布原创情景单元，尚未配置示范音视频；第三方视频/美剧须完成授权核验后再入库。

## 3. 目录结构说明

```text
.
├── src/                    # 学员端 Taro 应用
│   ├── api/                # 学员端 API 封装
│   ├── components/         # 公共业务组件
│   ├── constants/          # 品牌、文章等常量
│   ├── mock/               # 本地 Mock 服务
│   ├── pages/              # 学员端页面
│   ├── store/              # Pinia Store
│   ├── styles/             # 全局样式变量
│   └── utils/              # 工具函数
├── server/
│   ├── app/                # FastAPI 后端
│   │   ├── api/            # public/admin 路由
│   │   ├── core/           # 安全、权限、响应
│   │   ├── models/         # ORM 模型
│   │   ├── schemas/        # API DTO
│   │   └── services/       # 业务服务
│   ├── admin-web/          # 管理后台前端
│   ├── prompts/            # AI 出题提示词
│   ├── tests/              # 后端测试
│   └── requirements.txt    # Python 依赖
├── docker/                 # Nginx 与启动脚本
├── scripts/                # 部署、路由冒烟、文章解析等脚本
├── config/                 # Taro 构建配置
├── Dockerfile
├── docker-compose.yml
├── README.md
└── FEATURES.md             # 现有全量功能清单
```

## 4. 业务功能域

### 4.1 公考学习主线

公考主线由时政阅读、题目练习、知识框架、真题套卷、人民日报/申论和资料分析组成。

| 模块 | 学员端页面 | 后端服务 | 核心能力 |
| --- | --- | --- | --- |
| 时政文章 | `pages/article/*` | `article_service.py`、`study_service.py`、`featured_article.py` | HTML 页内全文阅读、今日推荐、读后考点练习 |
| 刷题练习 | `pages/question/*` | `quiz_service.py`、`question_service.py`、`wrong_service.py` | 多模式刷题、提交答案、错题记录、排行榜、统计 |
| 手动错题 | `pages/question/manual-*` | `manual_wrong_service.py` | 行测错题录入、图片上传、知识点关联、复习状态 |
| 知识框架 | `pages/knowledge/index` | `knowledge_service.py`、`knowledge_review_service.py` | Markdown 同步、树状知识点、笔记、星标、掌握度、复习 |
| 真题套卷 | `pages/exam/*` | `exam_service.py`、`exam_import.py` | 试卷列表、开考、答题、交卷、成绩和历史记录 |
| 人民日报/申论 | `pages/rmrb/*` | `rmrb_service.py`、`rmrb_meta_service.py`、`shenlun_service.py`、`vocab_inbox_service.py` | 时评 HTML、开采本、词表待收录、骨架模板、阶梯训练、四类题型练习与答案订正 |
| 资料分析 | `pages/ziliao/*` | `ziliao_service.py`, `ziliao_quick_calc_service.py` | 公式/题型/技巧、材料练习、速算训练与结果统计 |

### 4.2 素材积累与能力辅助

| 模块 | 学员端页面 | 后端服务 | 核心能力 |
| --- | --- | --- | --- |
| 语料本 | `pages/corpus/*` | `corpus_service.py` | 语料采集、标签、来源、知识点挂载、沉淀到规范词 |

### 4.3 个人成长与生活管理

| 模块 | 学员端页面 | 后端服务 | 核心能力 |
| --- | --- | --- | --- |
| 今日驾驶舱 | `pages/today/index` | `countdown_service.py`、`growth_service.py`、`review_hub_service.py`、`plan_service.py` | 考试倒计时、今日清单、复习提醒、昨日足迹 |
| 学习计划 | `pages/plan/*` | `plan_service.py` | 今日清单、本周计划、任务完成/跳过、每日复盘、模板同步 |
| 复习中心 | `pages/review/*` | `review_hub_service.py`、`srs.py` | 聚合文章错题、手动错题、知识点等到期复习 |
| 事件复盘 | `pages/events/*` | `event_impression_service.py` | 事件记录、情绪/印象复盘、时间线 |
| 成长足迹 | `pages/user/growth` | `growth_service.py` | 签到、学习分钟、正确率、积分和多领域进度聚合 |

### 4.4 账号、积分与基础能力

| 模块 | 相关文件 | 能力 |
| --- | --- | --- |
| 用户认证 | `auth_service.py`、`core/security.py`、`utils/auth.ts` | 学员登录注册、JWT、改密、资料更新 |
| 管理认证 | `api/deps.py`、`core/permissions.py` | 管理员 JWT、RBAC、权限矩阵 |
| 积分签到 | `user_service.py`、`growth_service.py` | 签到、积分流水、排行 |
| 上传 | `upload_paths.py`、`utils/upload.ts` | 头像、错题图 |
| Mock | `src/mock/service.ts` | 无后端演示和本地调试 |
| 主题 | `store/settings.ts`、`utils/theme.ts`、`utils/persistStorage.ts` | 深色/品牌色；H5 直写 localStorage 以免 Taro 二次 JSON 导致刷新丢主题 |

## 5. 数据模型概览

后端当前是 SQLite 单库，模型按领域拆分在 `server/app/models/`（base + 11 个域模块），由 `__init__.py` 统一 re-export。可以按领域理解：

| 领域 | 代表模型 |
| --- | --- |
| 权限与账号 | `Role`、`AdminUser`、`AppUser`、`SystemSetting` |
| 内容与题目 | `Category`、`Article`、`Question`、`StudyRecord`、`SectionRead` |
| 练习与复习 | `WrongAnswer`、`QuizAttempt`、`ManualWrong` |
| 积分成长 | `PointsLog`、`SignRecord` |
| 计划 | `PlanTask`、`PlanTemplate`、`DailyReview` |
| 知识框架 | `KnowledgeNode` |
| 真题套卷 | `ExamPaper`、`ExamQuestion`、`ExamAttempt`、`ExamAnswer` |
| 倒计时与行为 | `ExamCountdown`、`ActivityEvent` |
| 时政 | `TheoryPoint`、`ArticleQuizProgress`；`Article.brief_json` / `brief_status` |
| 人民日报/申论 | `RmrbArticle`、`DailyQuote`、`DailyQuoteSelection`、`DailyQuoteJob`、`ShenlunMaterial`、`ShenlunExercise`、`ShenlunExerciseJob`、`ShenlunExerciseAttempt`、`ShenlunMineLog`、`ShenlunNormTerm`、`ShenlunDrillLog`、`ShenlunTermCategory`、`ShenlunSkeletonTemplate`、`ShenlunSentenceType`、`ShenlunArgumentMethod`、`VocabInbox` |
| 时政/时评 HTML | `Article.content_html`；`RmrbArticle.content_html`；示范 `ShenlunTeachingExample.display_html` |
| 事件复盘 | `EventImpression` |
| 语料与资料分析 | `CorpusItem`、`ZiliaoFormula`、`ZiliaoQuestionType`、`ZiliaoTrick`、`ZiliaoPracticeLog`、`ZiliaoQuickMethod`、`ZiliaoQuickMethodVersion`、`ZiliaoQuickSession` |
| 摄影学习 | `PhotographyStage`、`PhotographyLesson`、`PhotographyCase`（含授权信息、观察/推断、EXIF 和练习任务） |

## 6. 接口分层

### 6.1 学员端 API

学员端接口统一挂在 `/api`，主要分组：

- `/api/config`：公开配置，如是否允许注册。
- `/api/auth/*`：学员注册、登录。
- `/api/user/*`：个人资料、头像、改密。
- `/api/articles/*`、`/api/questions`、`/api/answer`：文章与刷题；`/api/quiz-progress`：时政套题进度。
- `/api/theory-points`：学员端已发布时政要点；`/api/quotes`：已启用金句素材。
- `/api/photography/catalog`：公开已发布摄影课程、知识地图和经授权审核的摄影案例。
- `/api/wrong/*`、`/api/manual-wrong/*`：错题本。
- `/api/review/*`、`/api/knowledge/review/*`：复习中心与知识点复习。
- `/api/plan/*`：学习计划。
- `/api/knowledge/*`：知识框架。
- `/api/exam/*`：真题套卷。
- `/api/countdown`：目标考试倒计时（GET/PUT/DELETE）。
- `/api/rmrb/*`：人民日报/申论。
- `/api/ziliao/*`：资料分析。
- `/api/ziliao/quick-calc/*`：速算方法、训练会话、逐题答题、会话完成、个人历史及错题重练。
- `/api/events/*`、`/api/corpus/*`：事件复盘、语料本。

### 6.2 管理端 API

管理端接口统一挂在 `/admin`，需管理员 Token 和权限：

- `/admin/auth/*`：管理登录与当前用户。
- `/admin/articles/*`、`/admin/questions/*`、`/admin/categories/*`：内容和题库；分类待收录 `/admin/categories/vocab-inbox*`。文章要点由后台文章流程维护。
- `/admin/theory-briefs/*`：时政要点编排，读写分别要求 `article:read` / `article:write`.（路径挂载前缀为 `/admin`）
- `/admin/users/*`：用户管理。
- `/admin/settings/*`、`/admin/roles/*`、`/admin/permissions`：系统设置和权限。
- `/admin/knowledge/*`：知识框架管理。
- `/admin/plan/*`：计划模板。
- `/admin/exam/*`：试卷题库。
- `/admin/daily-quotes*`：金句列表/详情、录入编辑、JSON导入预检/提交/导出、日期精选、任务状态与手动整理；包含审核与客户端启用状态。读写分别要求rmrb:read / rmrb:write；后台调度独立于已退役全量档案。
- `/admin/rmrb/*`：时评文章、词表 CRUD、待收录 `/admin/rmrb/vocab-inbox*`、三刀导入。
- `/admin/ziliao/*`：资料分析资源。
- `/admin/ziliao/quick-calc/*`：速算规则维护、样题校验/发布和训练效果统计（`ziliao:read` / `ziliao:write`）。

## 7. 运行与部署

### 7.1 本地开发

学员端：

```bash
npm run dev:h5
```

默认 H5 开发端口是 `10087`。`USE_MOCK=true` 时使用前端 Mock；否则请求真实后端。

后端：

```bash
cd server
source .venv/bin/activate
uvicorn app.main:app --reload --port 8001
```

管理后台：

```bash
cd server/admin-web
npm run dev
```

### 7.2 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./data/zhengkao.db` | 后端数据库 |
| `SECRET_KEY` | 开发默认值 | JWT 密钥，生产必须修改 |
| `ALLOW_REGISTER` | `true` | 是否开放学员端自助注册 |
| `CORS_ORIGINS` | `http://localhost:10087` | 允许综合 H5 本地跨域访问 |
| `HTTP_PORT` / `HTTP_BIND` | `8081` / `127.0.0.1` | 容器宿主监听端口与绑定地址（部署用） |
| `BACKUP_DIR` / `BACKUP_RETENTION_DAYS` | `/opt/backups` / `14` | 备份目录与保留天数 |
| `KNOWLEDGE_KB_DIR` | 空 | 知识框架本地目录（生产留空） |
| `USE_MOCK` | `false` | 前端是否启用 Mock |
| `TARO_APP_API_URL` | `http://127.0.0.1:8001` | 前端 API 地址，Docker 同域时可为空 |
| `LLM_ENABLED` | `false` | 是否启用 AI 出题等能力 |
| `LLM_BASE_URL` / `LLM_MODEL` | DeepSeek 相关默认值 | LLM 服务配置 |
| `ASR_PROVIDER` | `none` | 云端语音识别供应商 |

### 7.3 Docker 部署

`Dockerfile` 分三段构建：

1. Node 20 bookworm 构建 Taro H5 到 `dist/`。
2. Node 20 alpine 构建管理后台到 `server/admin-dist/`。
3. Python 3.12 slim 运行 FastAPI，同时安装 Nginx 承载 H5。

`docker-compose.yml`（compose 项目名 `zhixing-gongkao`）默认把宿主机 `127.0.0.1:8081` 映射到容器内 `80`（可用 `.env` 的 `HTTP_BIND` / `HTTP_PORT` 调整），带健康检查，并把后端 `data` 目录挂到 Docker volume。容器内 Nginx 负责 H5 静态资源与 `/api`、`/admin`、`/manage`、`/uploads`、`/health` 的反代分流；上传文件、SQLite 数据库等运行态数据都在 `server/data`，备份需整包 tar（见 `deploy/backup.sh`）。

一键部署：`deploy/setup-docker.sh`（一次性装 Docker）+ `deploy.sh`（构建启动 + 健康检查 + 路由验证）；单机域名网关配置见 `deploy/nginx.conf`，完整手册见 [`DEPLOY.md`](./DEPLOY.md)。

## 8. 关键业务流程

### 8.1 阅读到练习

```text
管理员导入/维护文章
    -> 文章发布
    -> 学员端首页推荐/文章列表
    -> 学员阅读全文（HTML 页内渲染）
    -> 考点练习
    -> 提交答案
    -> 生成答题结果、积分、错题、统计
```

### 8.2 错题与复习

```text
答错题目或手动录入错题
    -> 写入 WrongAnswer / ManualWrong
    -> 按记忆曲线计算 next_review_at
    -> 复习中心聚合到期任务
    -> 作答/复习后推进阶段或重置
```

### 8.3 知识框架同步

```text
Obsidian Markdown / 管理端上传
    -> knowledge_service 解析
    -> 写入 KnowledgeNode
    -> 学员端树状浏览
    -> 节点笔记、星标、掌握度与复习
```

内置科目以 `tree_key` 作为稳定身份。服务端在结构化草稿保存、Markdown 导入、版本发布和激活时校验科目标题，阻止其他科目的结构被误发布到当前树。

### 8.4 真题套卷

```text
管理端维护试卷和题目
    -> 学员选择试卷
    -> start_attempt 创建考试记录
    -> 逐题 submit_answer
    -> finish_attempt 交卷
    -> 查看成绩、解析和历史记录
```

### 8.5 计划与成长

```text
管理端维护周计划模板
    -> 后端同步生成用户每日任务
    -> 学员完成/跳过/新增任务
    -> 每日复盘
    -> growth_service 汇总签到、分钟、正确率、积分、多领域进度
```

## 9. 架构特点与注意事项

- 后端业务集中在一个 FastAPI 单体内，适合个人项目快速迭代。
- ORM 模型 / schema / 路由已按领域拆分为多文件，`__init__.py` 与聚合入口保持原有 import 兼容。
- 旧库兼容逻辑写在 `main.py` 启动阶段，适合 SQLite 小规模迁移；长期建议引入 Alembic。
- 前端 API 封装已按业务域拆分到 `src/api/domains/`，`index.ts` 聚合导出 `api` 对象，调用方无需改动。
- 学员端页面很多，`app.config.ts` 是了解功能覆盖面的最直接入口。
- 管理后台权限采用菜单权限和接口权限双层控制，权限定义集中在 `server/app/core/permissions.py`。
- 上传文件不进 SQLite，部署和迁移时必须同时备份数据库和 `data/uploads`。
- `FEATURES.md` 已经覆盖较细的功能清单；本文档重点是架构、模块边界和业务流。


### 每日金句部署状态与数据生命周期（2026-10-13）
截至2026-10-13部署版本（提交`f641895`），默认北京时间06:40每日整理，08:00停止自动重试。运行状态用数据库唯一刊期与CAS领取，多进程不重复执行；中断超过2小时可重试。该版本全文不进入业务表、附件或任务日志；仅每句附近必要连续文本作为证据。10月13日时生产LLM凭据尚未配置；10月15日已启用，之后的本地流程变更见下文。
旧表定义仅留作迁移兼容，当前管理API不再访问。生产旧档案已停服后备份清理；快照位于`data/backups/rmrb-retirement-20261013-214526/`。生产已导入36条金句、72个仿写，全部待核对。


### 人民日报素材采集与质量优化（生产基线已运行；2026-10-18修复本地待部署）

- 金句、词汇和申论素材共用 `RmrbDailyPoolIssue` / `RmrbDailyPoolArticle` 发现纸版版面目录、合并跨版重复链接并缓存正文；正文与完整联合分析结果最长48小时，目录元数据保留7天，由后台小时清理。正式文章档案仍由档案模块负责。
- 词汇任务默认06:40启动，按不超过24,000字的完整文章批次每篇调用一次联合分析，输出评论类别、最多3条金句、词汇及申论素材候选。三类结果分别执行来源校验、去重与入库；申论素材按闭集、原文证据、8/10质量门和类型规则校验后仅保存为待审核，人工确认前不可用或发布。候选和正文指纹一起缓存，重试时优先复用，金句任务07:10复用评论类别和金句候选；缺失或旧规则缓存才重新分析。金句任务等待联合批次结束，窗口延长至10:00。若生产环境显式设置调度变量，部署时需同步调整为先联合分析、后金句。
- 素材概念分为来源文章、带原文证据的候选、人工审核后的学习条目和运营发布内容；金句、词汇和申论素材属于不同用途的候选视图，原文匹配不等于教学审核通过。`issue_date` / `source_date`代表报纸或文章发布日期，`collected_date`代表采集批次日期，`created_at`代表系统入库时间；不能互相替代。申论素材规则版本升至`1.1.0`，接受模型稳定英文评分键后归一为中文维度。
- 金句初筛只生成原句、主题、结构和质量说明，不生成仿写；通过人工审核并进入当天运营精选后，后台按需为已精选金句生成两种主题的作文示例。重复选择不会重复生成已有示例。
- 明确评论栏目和常见评论栏目直接识别，普通非评论标题不进入金句筛选；少量含评论特征的未知栏目才调用小批量目录分类。`DAILY_QUOTES_INCLUDE_EXTENDED=false` 默认关闭理论/建言/文艺扩展池，可按需开启。联合分析通过原文逐字证据、长度、质量分和直接引语规则后仍须人工审核。
- `LlmUsageLog` 记录调用模块、模型、状态、token和耗时，不保存提示词/文章正文/模型原始响应；管理端“大模型用量”按中国日期汇总，按配置的每百万token输入/输出单价估算费用。价格为零时只显示token与调用，不伪造费用。
- 采集失败可重试，已完成词汇文章按进度跳过；内容按刊期及来源去重，不覆盖人工审核结论。申论评分键在 AI 英文标识与后台中文名称间归一；证据匹配只允许空白差异并保存原文切片；无效候选和质量门槛拒绝分别按原因计数。词汇新增重点/可迁移/拓展补充优先级，旧数据默认展示为拓展补充。联合分析规则版本为`2026-10-18-combined-v3`，失效旧缓存；本轮修复已在本地修改，尚未部署，也未在生产重跑历史批次。

### 2026-10-15 · 本地速算生成与双端公式渲染

- `src/utils/quickCalc.ts` 是无网络的教学模拟题生成器，按七类方法场景构造数据；`QuickQuestion.check` 保留精确校验参数。四选项去重，比较用整数交叉乘积，计算题按题干指定精度设置唯一答案。
- `src/pages/ziliao/quick-calc.vue` 承载题型选择、训练、解析与结果；路由位于资料分析分包。服务端 `ziliao_quick_calc_service.py` 按已发布规则生成题目并在逐题提交时判分；训练按计算概念组织，多分数比较/排序、计算辨析与综合材料辨析作为题目形式组合，解题建议在答题后显示。增长量题基于真实统计/真题数据改编，按数据特征推荐除乘转化、乘数拆分、假设估算或错位加减等方法。`ZiliaoQuickSession` 保存题目快照、规则版本、答案与耗时，支持账号历史和错题重练。统计通过 `activity_service.record_event()` 写 `quick_calc_done`，禁止直接写 `activity_events`。速算训练不进入材料题积分或排行。
- `LatexBlock` 静态依赖 `formulaRenderer`，由 Taro 解析 `.weapp.ts` / `.h5.ts`；禁止在小程序中动态 import 源码 alias，否则可能留下未解析 require。微信端通过 `@rojer/katex-mini` 和既有 KaTeX 转换为 rich-text nodes，H5 使用 HTML；`MathText` 识别显式行内/块公式及 latex/math/tex 围栏。
- 依赖覆盖将 katex-mini 的旧 peer 范围绑定至根项目锁定的 KaTeX；该库依赖 KaTeX 内部 DOM API，升级任一依赖后须运行数学/渲染验证脚本。`weappMathChunk` 固定共享引擎在主包，防止主包同步引用资料分包。`weappMathStyles` 读取依赖样式，将字体替换为本地 woff2 data URL 并注入 Taro comp.wxss，不依赖字体 CDN。
- `scripts/check-quick-calc.mjs` 验证生成答案、条件、选项、公式与暗色根号；`scripts/check-weapp-math.mjs` 检查主包 2MB 限制、同步依赖边界、字体、公式引擎和路由。实现状态为本地，未部署发布；真机视觉验收待做。


### 2026-10-17 · 速算训练按题型组织（本地实现，待部署）

速算训练统一为分数比较、增长量、增长率、基期量四种题型。分数比较在同一组内覆盖分数性质、差分比较、同位比较和分母拆分场景，作答前只展示数据，作答后解析给出优先建议与推导。管理端按题型配置、预览和发布；新增分数比较规则初始为草稿，需显式发布。旧比较方法规则、版本及训练快照保留，历史统计和薄弱项推荐归入分数比较，建议方法分布单独统计。无需新增权限、菜单或环境变量。

### 2026-10-17 · 速算训练扩展题目形式（本地实现，待部署）

训练仍按计算概念归类，生成时再组合题目形式。分数比较包含两数符号比较、四分数选极值和完整排序；增长量、增长率、基期量包含直接计算及四选项计算辨析（唯一正确项或唯一错误项）。服务端生成后、练习会话落库前独立校验分数顺序、题目选项和计算辨析真值；答题记录新增题目形式统计。正式原题、公开数据改编题与教学模拟题应分别记录来源，当前多分数排序属于教学模拟，不代表真题频率或原题复现。

### 2026-10-17 · 混合训练综合材料辨析（本地实现，待部署）

混合训练达到 10/20 题时，每 10 题最多插入一题综合材料辨析，且仅在增长量、增长率、基期量均已发布时启用。题目从同源同单位的公开统计材料抽取四个指标，四个选项覆盖增长量、增长率、基期量和现期量；训练会话保存表格、公式编码、选项真值和题目形式快照。服务端按源数据重新计算并校验唯一正确项/错误项。学员端答题后接收逐项真值和公式解析；答题记录按 `mixed` 汇入“综合材料辨析”统计，不作为单一公式薄弱项推荐。

### 2026-10-18 · 速算训练概念扩展（本地实现，待部署）

速算规则扩展为比重、平均数、倍数、混合增长率、隔年增长率、年均增长、贡献率/拉动等概念题型，题面形式由生成器按规则轮换，解题技巧仅在答题后提供。隔年增长率独立按连续两期同比增速复合；年均增长包含年均复合增长率和年均增长量，复合增速题仅用两个以上增长年度的数据，解析保留开方精确式并提供对称近似和选项代入建议。数据来源包括国家统计局 2022—2024 年粮食分省产量与单产、分季节/分品种产量、2023—2024 年 GDP 现价产业构成，以及海关贸易统计。训练会话轮换真实数据样本；在重复检测时结合题型、题干和公式，避免相同题目重复，同时允许指标不同但数值相同的独立题目。增长量/增长率计算辨析仅使用在题面精度下可区分常见错项的数据样本（分别至少 2.5% 和 0.5% 增速），增长率训练覆盖低幅度及正负增长，不用人工算术误差补选项；更小增幅仍可用于其他题型。生成、预览、发布校验重新计算各类题目的答案和四项选项唯一性；训练效果按概念统计正确率和平均用时，并按题目形式记录各自正确率、平均用时和答题量。统计数据的改编练习不声明为真题复刻。资料分析知识框架的倍数关系同步更正为“倍数 = 1 + 增长率”。功能目前本地实现，部署前需逐项关联已发布且学员可见的知识节点并发布规则。

基期量训练同步改为基于官方两期数据出题，使用真实现期量与真实增速，按难度筛选样本并平衡正负增长。题干和解析显示来源、年份、单位；增速按一位小数展示，基期量按题面数据计算后取最接近值，避免将展示增速误解为数据原始精度。

### 2026-10-18 · 微信公众号推广入口快照（本地实现，待部署）

回复配置新增可选 `promotionEntries`，关键词新增可选 `entryId`，旧 JSON 兼容。`wechat_promotion_service.py` 提供无菜单订阅号的推广方案合并、受控页面目录和入口文本渲染。`POST /admin/wechat-replies/promotion-template` 需编辑权限，只返回合并结果，不保存或发布。未知绑定、目录外路径与空说明阻止发布。入口随规则共用既有不可变快照、回退与去重命名空间；无新增表、环境变量或权限。不包含菜单接口、卡片消息、动态跳转或归因采集。
