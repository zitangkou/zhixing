# 知行公考项目架构与业务功能梳理

> 更新时间：2026-08-13  
> 项目定位：纯公考备考应用（时政阅读、资料分析、申论、真题套卷、错题闭环、今日驾驶舱）。

## 1. 系统总览

本项目由四个主要部分组成：

| 部分 | 目录 | 技术栈 | 职责 |
| --- | --- | --- | --- |
| 学员端应用 | `src/` | Taro 4、Vue 3、TypeScript、NutUI、Pinia | 面向 H5 / 微信小程序的学习、练习、复盘、个人中心 |
| 后端 API | `server/app/` | FastAPI、SQLAlchemy 2、SQLite、JWT | 业务接口、数据持久化、鉴权、文件上传、启动初始化 |
| 管理后台 | `server/admin-web/` | Vue 3、Vite、Element Plus、Pinia | 内容、题库、用户、配置、权限和资源管理 |

整体形态是一个单体仓库、多前端入口的应用：

```text
H5 / 小程序学员端
        |
        | /api/*
        v
FastAPI 后端 ---- SQLite / data/uploads
        ^
        | /admin/*
管理后台 Vue 应用
```

生产 Docker 镜像会构建 H5、构建管理后台，然后把 H5 交给 Nginx，FastAPI 提供 API、上传文件与 `/manage/` 管理后台静态资源。

## 2. 技术架构

### 2.1 学员端

学员端位于 `src/`，使用 Taro 跨端运行：

- `src/app.config.ts`：声明全部页面路由、窗口样式和底部 Tab。
- `src/app.ts`：创建 Vue 应用、安装 Pinia、接入持久化、本地主题初始化和应用启动 bootstrap。
- `src/api/index.ts`：统一 API 客户端，负责真实 API / Mock 切换、Token 注入、401 处理、上传入口。
- `src/pages/`：业务页面，按模块拆分。
- `src/components/`：公共组件，如文章卡片、知识树、题目项、思维导图、反馈层、积分徽章等。
- `src/store/`：Pinia 状态，覆盖用户、题目、文章、计划、设置、知识、手动错题等。
- `src/utils/`：跨模块工具，如鉴权、媒体 URL、上传、记忆曲线、语音输入、知识树等。
- `src/mock/service.ts`：`USE_MOCK=true` 时的本地演示服务。

底部 Tab 有四个主入口：

| Tab | 页面 | 业务定位 |
| --- | --- | --- |
| 今日 | `pages/today/index` | 今日驾驶舱：考试倒计时、今日清单、复习提醒、昨日足迹、快捷操作 |
| 学习 | `pages/index/index` | 学习首页，聚合公考主线、能力拓展和推荐内容 |
| 练习 | `pages/question/index` | 刷题、错题、复习、套卷等练习入口 |
| 我的 | `pages/user/index` | 账号、签到、积分、排行、成长足迹和模块入口 |

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
| 文章管理 | 文章 CRUD、Markdown 导入、审核发布、分类、题目管理、AI 出题 |
| 分类管理 | 内容分类树维护 |
| 用户管理 | 学员账号、积分、状态管理 |
| 知识框架 | Markdown 上传、树同步、节点维护 |
| 学习计划 | 周计划模板维护、同步到待办 |
| 试卷题库 | 试卷、题目、批量导入 |
| 资料分析 | 公式、题型、秒杀技巧、练习资源 |
| 人民日报 | 时评文章、规范词、骨架模板、句式、论证方法 |
| 系统设置 | 键值配置、角色权限矩阵 |

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
| 时政文章 | `pages/article/*` | `article_service.py`、`study_service.py`、`featured_article.py` | 文章阅读、分节已读、推荐、思维导图、读后练习 |
| 刷题练习 | `pages/question/*` | `quiz_service.py`、`question_service.py`、`wrong_service.py` | 多模式刷题、提交答案、错题记录、排行榜、统计 |
| 手动错题 | `pages/question/manual-*` | `manual_wrong_service.py` | 行测错题录入、图片上传、知识点关联、复习状态 |
| 知识框架 | `pages/knowledge/index` | `knowledge_service.py`、`knowledge_review_service.py` | Markdown 同步、树状知识点、笔记、星标、掌握度、复习 |
| 真题套卷 | `pages/exam/*` | `exam_service.py`、`exam_import.py` | 试卷列表、开考、答题、交卷、成绩和历史记录 |
| 人民日报/申论 | `pages/rmrb/*` | `rmrb_service.py`、`rmrb_meta_service.py`、`shenlun_service.py` | 时评阅读、开采本、规范词、骨架模板、阶梯训练 |
| 资料分析 | `pages/ziliao/*` | `ziliao_service.py` | 公式库、题型库、技巧库、专项练习、结果统计 |

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
| 主题 | `store/settings.ts`、`utils/theme.ts` | 深色模式、本地持久化 |

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
| 人民日报/申论 | `RmrbArticle`、`ShenlunMineLog`、`ShenlunNormTerm`、`ShenlunDrillLog`、`ShenlunTermCategory`、`ShenlunSkeletonTemplate`、`ShenlunSentenceType`、`ShenlunArgumentMethod` |
| 事件复盘 | `EventImpression` |
| 语料与资料分析 | `CorpusItem`、`ZiliaoFormula`、`ZiliaoQuestionType`、`ZiliaoTrick`、`ZiliaoPracticeLog` |

## 6. 接口分层

### 6.1 学员端 API

学员端接口统一挂在 `/api`，主要分组：

- `/api/config`：公开配置，如是否允许注册。
- `/api/auth/*`：学员注册、登录。
- `/api/user/*`：个人资料、头像、改密。
- `/api/articles/*`、`/api/questions`、`/api/answer`：文章与刷题。
- `/api/wrong/*`、`/api/manual-wrong/*`：错题本。
- `/api/review/*`、`/api/knowledge/review/*`：复习中心与知识点复习。
- `/api/plan/*`：学习计划。
- `/api/knowledge/*`：知识框架。
- `/api/exam/*`：真题套卷。
- `/api/countdown`：目标考试倒计时（GET/PUT/DELETE）。
- `/api/rmrb/*`：人民日报/申论。
- `/api/ziliao/*`：资料分析。
- `/api/events/*`、`/api/corpus/*`：事件复盘、语料本。

### 6.2 管理端 API

管理端接口统一挂在 `/admin`，需管理员 Token 和权限：

- `/admin/auth/*`：管理登录与当前用户。
- `/admin/articles/*`、`/admin/questions/*`、`/admin/categories/*`：内容和题库。
- `/admin/users/*`：用户管理。
- `/admin/settings/*`、`/admin/roles/*`、`/admin/permissions`：系统设置和权限。
- `/admin/knowledge/*`：知识框架管理。
- `/admin/plan/*`：计划模板。
- `/admin/exam/*`：试卷题库。
- `/admin/rmrb/*`：人民日报/申论元数据。
- `/admin/ziliao/*`：资料分析资源。

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
| `CORS_ORIGINS` | `http://localhost:10086,http://localhost:10087,http://localhost:10088,http://localhost:10089` | 允许综合版、申论与政治理论本地前端跨域访问 |
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
    -> 学员阅读并记录分节进度
    -> 进入文章刷题
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
