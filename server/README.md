# 知行后端

全仓产品矩阵、H5/小程序功能、后台菜单及操作发布流程见[项目功能与操作手册](../docs/PROJECT_OPERATIONS_MANUAL.md)。

轻量级 **FastAPI + SQLite + APScheduler** 架构，支持数据持久化、定时爬取、管理后台 RBAC。

## 架构选型

| 组件 | 选型 | 说明 |
|------|------|------|
| Web 框架 | FastAPI | 轻量、异步、自带 Swagger |
| 数据库 | SQLite (WAL) | 零配置持久化，可换 PostgreSQL |
| ORM | SQLAlchemy 2.0 | 类型安全 |
| 认证 | JWT + RBAC | 管理端角色权限 |
| 定时任务 | APScheduler | 每日自动爬取文章 |
| 爬虫 | httpx + 可扩展 | 当前内置模拟源，可接 RSS/真实站点 |

## 快速启动

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# 启动（默认 http://127.0.0.1:8001）
uvicorn app.main:app --reload --port 8001
```

- API 文档：http://127.0.0.1:8001/docs
- 健康检查：http://127.0.0.1:8001/health

## 默认管理员

- 用户名：`admin`
- 密码：`admin123`

## API 分组

### 公开接口 `/api/*`（对接 Taro 前端）

- `GET /api/articles/daily` — 今日推荐
- `GET /api/articles/{id}` — 文章详情
- `GET /api/questions?articleId=` — 题目列表
- `POST /api/answer` — 提交答案
- `POST /api/signin` — 签到
- `GET /api/points/log` — 积分流水
- `GET /api/rank?type=weekly` — 排行榜
- 等（与前端 Mock 契约一致）

移动端请求头：`X-User-Id: u-demo-001`（开发阶段标识用户）

### 管理接口 `/admin/*`（需 Bearer Token）

- `POST /admin/auth/login` — 登录
- 文章 CRUD `/admin/articles`
- 试题 CRUD `/admin/questions`
- 用户管理 `/admin/users`
- 系统设置 `/admin/settings`
- 角色权限 `/admin/roles`、`/admin/permissions`
- 爬虫 `POST /admin/crawler/run`、`GET /admin/crawler/logs`

## 角色权限

| 角色 | 权限 |
|------|------|
| super_admin | 全部 |
| editor | 文章/试题/爬虫/用户查看 |
| viewer | 只读 |

## 前端对接

默认已 **关闭 Mock**，直连 `http://127.0.0.1:8001`。

```bash
# 终端 1：后端
cd server && source .venv/bin/activate
uvicorn app.main:app --reload --port 8001

# 终端 2：H5 前端
npm run dev:h5

# 若需临时使用 Mock（含 rmrb/dushu/足迹等）：
USE_MOCK=true npm run dev:h5
```

冒烟测试（独立临时库）：

```bash
cd server && source .venv/bin/activate
python -m pytest tests/test_api_smoke.py -q
```

环境变量（可选）：

- `TARO_APP_API_URL` — API 地址（生产部署时改为 https://your-domain.com）
- `USE_MOCK=true` — 启用 Mock（生产勿开）

H5 开发时在 `.env` 的 `CORS_ORIGINS` 中加入前端地址（已含 10086/10087）。

### 新增用户数据 API（落库）

| 接口 | 说明 |
|------|------|
| `GET /api/user/me` | 用户信息、积分、签到日期 |
| `GET /api/study/records` | 学习记录 |
| `GET /api/study/section-reads` | 小节已读 |
| `POST /api/study/sections/read` | 标记小节已读 |
| `GET /api/wrong` | 错题本 |
| `POST /api/wrong/redo` | 错题重做 |
| `GET /api/review` | 复习任务（服务端计算） |

## 爬虫与文章结构

- **人民日报 RSS**：`politics.xml`、`legal.xml` 定时抓取
- 正文页解析后自动 **分章/节/段** 写入 `sections` JSON 字段
- 公开 API 返回 `sections` + 扁平 `content`（兼容出题）

手动触发：`POST /admin/crawler/run`

### 人民日报评论文章

管理端「人民日报 → 评论文章」复用全量电子报和客户端文章档案，先识别评论版及明确栏目名（如人民时评、今日谈、人民观点、金台随笔、和音、社论、微观等），再接收全量文章 AI 全文评估中高置信识别出的评论/社论稿。原文 Markdown/HTML 可预览；服务端 LLM 已启用时自动生成待审三刀解剖草稿（最多 2 篇并发），未启用时可逐篇手动提交。所有解剖稿都需人工编辑审核，通过后才标记为可用。文件存放在持久化数据目录 `server/data/rmrb/comments/`；不配置服务端 LLM 时，规则命中的原文归档仍可用。

### 人民日报全量文章 AI 评估

管理端「人民日报 → 全量文章」支持逐篇/批量全文评估、按评估状态筛选和查看报告；全量采集完成后会自动排队。需配置服务端 `LLM_ENABLED=true` 与 `LLM_API_KEY` 才会调用模型；未配置时记录保留为待评估。报告分别判断文章体裁和评论/观点属性，并包括申论关联、主题、适用场景、摘要、观点、结构、六项评分、原文证据和物料建议。评分按主题价值 20%、可迁移性 25%、事实素材 20%、表达质量 15%、论证结构 10%、时效性 10%折算。高/中关联文章保存正文文件版本，低关联正文仅用于本次评估并保留正文哈希与报告。AI 建议不直接覆盖最终分类；人工确认时核验原文证据，无法定位的证据会阻止确认。全文模型识别为评论/观点稿的文章可同步进入评论物料流程。评估结果存于 `rmrb_article_evaluations`，正文仍以档案文件版本存储，不放入 SQLite 正文列。

## 管理后台（admin-web）

管理 **UI** 与 **API** 路径分离，避免冲突，便于单进程部署：

| 用途 | 路径 |
|------|------|
| 管理页面 | `/manage/` |
| 管理 API | `/admin/*` |
| 移动端 API | `/api/*` |

### 开发

```bash
# 终端 1：后端
cd server && source .venv/bin/activate
uvicorn app.main:app --reload --port 8001

# 终端 2：管理前端
cd server/admin-web && npm run dev
# 访问 http://localhost:5173/manage/
```

Vite 仅将 `/admin` 代理到后端 API，页面由 dev server 在 `/manage/` 提供。

### 生产（单进程）

```bash
cd server/admin-web && npm run build   # 产出 server/admin-dist
cd server && uvicorn app.main:app --host 0.0.0.0 --port 8001
# 访问 http://your-host:8001/manage/
```

构建产物存在时，FastAPI 自动挂载 `admin-dist` 到 `/manage`。

## 生产部署

1. 将 `DATABASE_URL` 换为 PostgreSQL
2. 修改 `SECRET_KEY`、`ADMIN_PASSWORD`
3. 使用 gunicorn + uvicorn workers 或 Docker 部署
4. 爬虫模块替换 `CRAWL_SOURCES` 为真实 RSS/站点解析逻辑
